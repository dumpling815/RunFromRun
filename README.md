
About Docker & Claude Desktop 
# Build image by following command.
# docker buildx build --env-file .env -t (your_repository):(tag) --push .
# To make mounting directory, enter following command in terminal
# ./touch_mount_dir.sh
# Write down following docker command correctly in your claude_desktop_config.json
docker run --env-file {.env file location} -v {$HOME/rfr_pdf_results}:{/rfr/pdf_results} -i {image}
# Note that you should replace $HOME with your pc's home directory path. 