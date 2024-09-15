#!/bin/bash

# Test inotifywait using csync config

file_events="create,modify,move,delete,attrib" # No spaces in this list

#cfg_path=/usr/local/etc
cfg_path=/etc/csync2
cfg_file=csync2.cfg

# Parse csync2 config file for included and excluded locations
while read -r key value
do
	# Ignore comments and blank lines
	if [[ ! $key =~ ^\ *# && -n $key ]]
	then
		if [[ $key == "include" ]]
		then
			includes=("${includes[@]}" "${value%;}")
		elif [[ $key == "exclude" ]]
		then
			excludes=("${excludes[@]}" "${value%;}")
		fi
	fi
done < "$cfg_path/$cfg_file"

echo " INC: ${includes[*]}"
echo " EXC: ${excludes[*]}"

if [[ ${#includes[@]} -eq 0 ]]
then
	echo "No include locations found"
	exit 1
fi

# Monitor for events and pipe triggered files
inotifywait --monitor --recursive  --event $file_events "${includes[@]}" | while read -r inotifyout
do
	# Check if excluded
	for excluded in "${excludes[@]}"
	do
		# Check if filepath begins with excluded path
		if [[ $inotifyout == $excluded* ]]
		then
			# Excluded - skip this file and return to inotifywait
			echo "EXCLUDED: $inotifyout"
			continue 2
		fi
	done

	echo "$inotifyout"
done
