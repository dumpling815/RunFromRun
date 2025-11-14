# SETUP
---
## Dockerfile
Dockerfile is given in this project.

If you want to build your custom images, use following docker command.
```bash
docker buildx build --env-file .env -t (your_repository):(tag) --push .
```
## Mounting Directory
This project leverages local ollama engine, which results in high overhead.

So we leverage cache of pdf analysis result by mounted directory.

To make correct directory in your system, use 'touch_mount_dir.sh' in this project.
```bash
./touch_mount_dir.sh
```
## Claude Desktop
This project leverages claude desktop's MCP client for default.

### Configuration
To use pdf result caching logic in this.
Correctly use following docker command in claude_desktop_config.json.
If you correctly used script above, you can use the command.

```bash
docker run --env-file {< your.env file location >} -v {< your $HOME path > /rfr_pdf_results}:{/rfr/pdf_results} -i {image}
```
Note that you should replace $HOME with your pc's home directory path. 