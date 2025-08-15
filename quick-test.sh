#!/bin/bash

source ./venv/bin/activate

function generate() {
	ollama list \
		| tail -n+2 \
		| while IFS=" " read -ra ROW;
			do echo "${ROW[0]}";
		done
}

function test() {
	while read -r MODEL; do
		python scripts/simple_verbose_runner.py \
			--model ${MODEL} \
			--level 1 \
			--max-retries 1
	done<<<$(generate | grep "${1}")
}

test
