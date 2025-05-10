#!/bin/bash
# Script to add memory = "512Mi" to all function definitions in variables.tf

# Path to the variables.tf file
FILE="terraform/modules/cloud_functions/variables.tf"

# Temporary file
TMP_FILE="terraform/modules/cloud_functions/variables.tf.tmp"

# Create a temporary file
cp "$FILE" "$TMP_FILE"

# Process the file
while IFS= read -r line; do
  echo "$line" >> "$FILE.new"
  if [[ "$line" =~ env_vars[[:space:]]*=[[:space:]]*\{\} ]]; then
    # Check if the next line already has memory setting
    next_line=$(grep -A 1 -F "$line" "$TMP_FILE" | tail -n 1)
    if [[ ! "$next_line" =~ memory[[:space:]]*= ]]; then
      echo '      memory      = "512Mi"' >> "$FILE.new"
    fi
  fi
done < "$TMP_FILE"

# Replace the original file
mv "$FILE.new" "$FILE"

# Clean up
rm "$TMP_FILE"

echo "Memory settings added to all functions in $FILE"
