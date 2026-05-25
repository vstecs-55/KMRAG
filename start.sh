#!/bin/bash
cd "/home/admin/Documents/Projects/KM RAG"
export PYTHONPATH=$PYTHONPATH:.
/home/linuxbrew/.linuxbrew/bin/python3 -u app.py >> server_v2.log 2>&1
