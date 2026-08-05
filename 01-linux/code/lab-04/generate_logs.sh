#!/bin/bash
# Generate 500 realistic nginx access log entries

IPS=("192.168.1.10" "10.0.0.5" "172.16.0.100" "203.0.113.50" "198.51.100.25"
     "192.168.1.11" "10.0.0.6" "203.0.113.51" "172.16.0.101" "198.51.100.26")

PATHS=("/api/v1/users" "/api/v1/products" "/api/v1/orders" "/" "/login" 
       "/api/v1/health" "/static/css/main.css" "/api/v1/search" "/admin" "/api/v1/payments")

STATUSES=("200" "200" "200" "200" "200" "200" "200" "301" "304" "400" "401" "403" "404" "404" "500" "502" "503")

AGENTS=("Mozilla/5.0 Chrome/120.0" "curl/7.88.1" "python-requests/2.31" "PostmanRuntime/7.36" "Googlebot/2.1")

for _ in $(seq 1 500); do   # _ = the counter is unused
    ip=${IPS[$RANDOM % ${#IPS[@]}]}
    path=${PATHS[$RANDOM % ${#PATHS[@]}]}
    status=${STATUSES[$RANDOM % ${#STATUSES[@]}]}
    size=$((RANDOM % 50000 + 100))
    agent=${AGENTS[$RANDOM % ${#AGENTS[@]}]}
    
    # Generate timestamps across last 24 hours
    hour=$(printf "%02d" $((RANDOM % 24)))
    minute=$(printf "%02d" $((RANDOM % 60)))
    second=$(printf "%02d" $((RANDOM % 60)))
    
    echo "$ip - - [15/Jan/2024:${hour}:${minute}:${second} +0000] \"GET $path HTTP/1.1\" $status $size \"-\" \"$agent\""
done
