#!/usr/bin/zsh
# For every .bril file in the given directory, compare the output of the file with and without ssa
input="test/ssa/tests"
while read -r FILE
do
    echo "${FILE}"
    OLD=$(bril2json < ${FILE} | brili)
    NEW=$(bril2json < ${FILE} | python3 ssa.py | brili)
    if [[ ${OLD} == ${NEW} ]]
    then
        echo ": OK"
    else
        echo "Failed: expected ${OLD}, got ${NEW}"
    fi
done < ${input}