// Create new group:
curl -X POST -H "Content-Type: application/json" -d "{\"groupName\": \"test_group\"}" http://localhost:8082/groups

// Delete group:
curl -X DELETE -H "Content-Type: application/json" http://localhost:8082/groups/test_group

// add add user to group:
curl -X POST -H "Content-Type: application/json" -d "{\"userID\": 1}" http://localhost:8082/groups/test_group/users

// remove user from group:
curl -X DELETE -H "Content-Type: application/json" http://localhost:8082/groups/test_group/users/1


