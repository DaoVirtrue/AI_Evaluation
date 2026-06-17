#!/bin/bash
TOOL="$1"
INPUT="$2"
DANGEROUS=("rm -rf" "sudo" "DROP TABLE" "DELETE FROM" "__import__" "os.system" "subprocess")
for pattern in "${DANGEROUS[@]}"; do
    if echo "$INPUT" | grep -iq "$pattern"; then
        echo "⚠️ DANGEROUS: $TOOL matches '$pattern'"
        echo "Input: ${INPUT:0:200}..."
        echo "Proceed? (y/N)"
        read -r ans
        if [ "$ans" != "y" ]; then exit 1; fi
    fi
done
exit 0
