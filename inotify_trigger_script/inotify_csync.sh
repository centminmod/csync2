#!/bin/bash

# Watch csync directories and sync changes via csync2
#
# $1: csync2 options to passthrough


# --- SETTINGS ---

file_events="move,delete,attrib,create,close_write,modify" # File events to monitor - no spaces in this list
queue_file=/home/learn4gd/tmp/inotify_queue.log            # File used for event queue
csync_log=/home/learn4gd/tmp/csync_server.log              # File used for monitoring csync server timings

check_interval=0.5                   # Seconds between queue checks - fractions allowed
full_sync_interval=$((60*60))        # Seconds between a regular full sync - zero to turn off
num_lines_until_reset=200000         # Reset queue log file after reading this many lines
num_batched_changes_threshold=15000  # Number of changes in one batch that will trigger a full sync and reset
parallel_updates=1                   # Flag (0/1) to toggle updating of peers/nodes in parallel

#cfg_path=/usr/local/etc
cfg_path=/etc/csync2
cfg_file=csync2.cfg

# Separate all passed options for csync
csync_opts=("$@")


# --- VERSION ---

echo "CSync Controller"
echo "Version 13 Jan 2022 22:22"
echo
echo "Passed options: ${csync_opts[*]}"
echo
echo "* SETTINGS"
echo "  check_interval                = ${check_interval}s"
echo "  full_sync_interval            = ${full_sync_interval}s"
echo "  num_lines_until_reset         = $num_lines_until_reset"
echo "  num_batched_changes_threshold = $num_batched_changes_threshold"
echo "  parallel_updates              = $parallel_updates"


# --- CSYNC SERVER ---

# Extract server-specific options
server_opts=()
if [[ $* =~ -N[[:space:]]?([[:alnum:]\.]+) ]]  # hostname
then
	this_node=${BASH_REMATCH[1]}
	server_opts+=(-N "$this_node") # added as two elements
else
	echo "*** WARNING: No hostname specified ***"
	sleep 2
fi
if [[ $* =~ -D[[:space:]]?([[:graph:]]+) ]]    # database path
then
	server_opts+=(-D "${BASH_REMATCH[1]}")
fi

echo
echo "* SERVER"
echo "  Options: ${server_opts[*]}"

# Start csync server outputting timings to log for monitoring activity status
csync2 -ii -t "${server_opts[@]}" &> $csync_log &
csync_pid=$!

# Wait for server startup then check
sleep 0.5
if ! ps --pid $csync_pid > /dev/null
then
	echo "Failed to start csync server"
	exit 1
fi

# Stop background csync server on exit
trap 'kill $csync_pid' EXIT

echo "  Running..."


# --- PARSE CSYNC CONFIG FILE ---

# Parse csync2 config file for included and excluded locations
while read -r key value
do
	# Ignore comments and blank lines
	if [[ ! $key =~ ^\ *# && -n $key ]]
	then
		if [[ $key == "host" && $value != $this_node* ]]
		then
			nodes+=("${value%;}")
		elif [[ $key == "include" ]]
		then
			includes+=("${value%;}")
		elif [[ $key == "exclude" ]]
		then
			excludes+=("${value%;}")
		fi
	fi
done < "$cfg_path/$cfg_file"

echo
echo "* CONFIG"
echo "  Peers:    ${nodes[*]}"
echo "  Includes: ${includes[*]}"
echo "  Excludes: ${excludes[*]}"

if [[ ${#includes[@]} -eq 0 ]]
then
	echo "No include locations found"
	exit 1
fi


# --- INOTIFY FILE MONITOR ---

echo
echo "* INOTIFY"

# Reset queue file
truncate -s 0 $queue_file

# Monitor for events in the background and add altered files to queue file
while read -r file
do
	# Check if excluded
	for excluded in "${excludes[@]}"
	do
		if [[ $file == $excluded* ]]
		then
			# Excluded - skip this file and return to inotifywait
			continue 2
		fi
	done

	# Add file to queue
	echo "$file" >> $queue_file

done < <(inotifywait --monitor --recursive --event $file_events --format "%w%f" "${includes[@]}") &

inotify_pid=$!

# Stop background inotify monitor and csync server on exit
trap 'kill $inotify_pid; kill $csync_pid' EXIT

sleep 1
echo "  Running..."


# --- HELPERS ---

# Wait until csync server is quiet
function csync_server_wait()
{
	# Wait until the end timestamp record appears in the last log line or if the file is empty
	until tail --lines=1 $csync_log | grep --quiet TOTALTIME || [[ ! -s $csync_log ]]
	do
		echo "...waiting for csync server..."
		sleep $check_interval
	done
}


# Run a full check and sync operation
function csync_full_sync()
{
	echo
	echo "* FULL SYNC"

	# First wait until csync server is quiet
	csync_server_wait

	if (( parallel_updates ))
	then
		# Check files separately from parallel update
		echo "  Checking all files"
		csync2 "${csync_opts[@]}" -cr "/"

		# Update each node in parallel
		update_pids=()
		for node in "${nodes[@]}"
		do
			echo "  Updating $node"
			csync2 "${csync_opts[@]}" -ub -P "$node" &
			update_pids+=($!)
		done
		wait "${update_pids[@]}"
	else
		# Check nodes in sequence
		echo "  Checking and updating peers sequentially"
		csync2 "${csync_opts[@]}" -x
	fi

	last_full_sync=$(date +%s)
	echo "  Done"
}


# Reset queue
function reset_queue()
{
	echo
	echo "* RESET QUEUE LOG"

	# Reset queue log file
	truncate -s 0 $queue_file
	queue_line_pos=1

	# Run a full sync in case inotify triggered during reset
	csync_full_sync

	# Reset csync server log too
	truncate -s 0 $csync_log
}


# --- QUEUE PROCESSING ---

# Run a full check and sync before queue processing begins - after file monitor started so no changes are missed in-between
csync_full_sync


# Periodically monitor inotify queue file
queue_line_pos=1
last_full_sync=$(date +%s)
while true
do
	# Delay between updates to allow for batches of inotify events to be gathered
	sleep $check_interval

	# Make array starting from last read position in queue file
	mapfile -t file_list < <(tail --lines=+$queue_line_pos $queue_file)

	if [[ ${#file_list[@]} -eq 0 ]]
	then
		# No new entries - quiet time

		# Check for reset
		if [[ $queue_line_pos -ge $num_lines_until_reset ]]
		then
			reset_queue

		# Check for regular full sync
		elif (( full_sync_interval && ($(date +%s) - last_full_sync) > full_sync_interval ))
		then
			csync_full_sync
		fi

		# Jump back to sleep
		continue
	fi

	echo
	echo "* PROCESSING QUEUE (line $queue_line_pos)"

	# Advance queue file position
	((queue_line_pos+=${#file_list[@]}))

	# Remove duplicates
	mapfile -t csync_files < <(printf "%s\n" "${file_list[@]}" | sort -u)

	# DEBUG: Output files processed in each cycle
	# printf "%s\n" "${csync_files[@]}" >> "/tmp/csync_$(date +%s%3N).log"

	# Check number of files in this batch
	if [[ ${#csync_files[@]} -ge $num_batched_changes_threshold ]]
	then
		# Large batch - run full sync and reset
		# This avoids breaching any max file argument limits and also acts as a safety net if inotify misses events when there are many changing files
		echo "* LARGE BATCH (${#csync_files[@]} files)"

		csync_full_sync

		# Jump back to sleep
		continue
	fi

	# Wait until csync server is quiet
	csync_server_wait

	# Process files by sending csync commands
	# Split into two stages so that outstanding dirty files can be processed regardless of when or where they were marked

	#   1. Check and possibly mark queued files as dirty - recursive so nested dirs are handled even if inotify misses them
	echo "  Checking ${#csync_files[@]} files"
	csync2 "${csync_opts[@]}" -cr "${csync_files[@]}"

	#   2. Update outstanding dirty files on peers
	if (( parallel_updates ))
	then
		# Update each node in parallel
		update_pids=()
		for node in "${nodes[@]}"
		do
			echo "  Updating $node"
			csync2 "${csync_opts[@]}" -ub -P "$node" &
			update_pids+=($!)
		done
		wait "${update_pids[@]}"
	else
		# Update nodes in sequence
		echo "  Updating peers sequentially"
		csync2 "${csync_opts[@]}" -u
	fi

	echo "  Done"
done
