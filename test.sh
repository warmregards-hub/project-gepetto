#!/bin/bash
TOKEN=$(curl -s -X POST "http://localhost:8000/api/auth/token" -d "username=admin&password=gepetto" | jq -r .access_token)
echo "Got token: $TOKEN"
curl -s -X POST "http://localhost:8000/api/agent/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Make a mock video of a dog with veo-3.1", "project_id": "test_project_uuid"}' | jq
