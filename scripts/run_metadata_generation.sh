#!/bin/bash

# 메타데이터 생성 스크립트를 백그라운드에서 실행하는 스크립트
# 사용법: ./scripts/run_metadata_generation.sh [입력파일] [출력파일] [처리할 항목 수]

# 기본값 설정
INPUT_FILE=${1:-"data/processed/stretching_filtered_data.json"}
OUTPUT_FILE=${2:-"data/enhanced/enhanced_data.json"}
LIMIT=${3:-""}

# 출력 디렉토리 생성
mkdir -p data/enhanced
mkdir -p logs

# 현재 시간을 로그 파일명에 사용
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="logs/metadata_generation_${TIMESTAMP}.log"

echo "메타데이터 생성 시작..."
echo "입력 파일: $INPUT_FILE"
echo "출력 파일: $OUTPUT_FILE"
if [ -n "$LIMIT" ]; then
    echo "처리할 항목 수: $LIMIT"
    LIMIT_ARG="--limit $LIMIT"
else
    echo "모든 항목 처리"
    LIMIT_ARG=""
fi
echo "로그 파일: $LOG_FILE"

# nohup을 사용하여 백그라운드에서 실행
nohup python scripts/generate_metadata_openai.py --input "$INPUT_FILE" --output "$OUTPUT_FILE" $LIMIT_ARG > "$LOG_FILE" 2>&1 &

# 프로세스 ID 저장
PID=$!
echo "프로세스 ID: $PID"
echo "프로세스 ID를 logs/last_pid.txt에 저장합니다."
echo $PID > logs/last_pid.txt

echo "백그라운드에서 실행 중입니다. 로그를 확인하려면 다음 명령어를 사용하세요:"
echo "tail -f $LOG_FILE"
echo ""
echo "프로세스를 종료하려면 다음 명령어를 사용하세요:"
echo "kill $PID" 