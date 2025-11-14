# SETUP
---
## Dockerfile
Dockerfile is given in this project

## Claude Desktop
This project leverages claude desktop's MCP client for default.

### Configuration
To use pdf result caching logic in this 
Correctly use following docker command in claude_desktop_config.json
docker run --env-file {< your.env file location >} -v {< your $HOME path> /rfr_pdf_results}:{/rfr/pdf_results} -i {image}

About Docker & Claude Desktop 
# Build image by following command.
# docker buildx build --env-file .env -t (your_repository):(tag) --push .
# To make mounting directory, enter following command in terminal
# ./touch_mount_dir.sh

# Note that you should replace $HOME with your pc's home directory path. 