FROM ghcr.io/ggml-org/llama.cpp:server

# Copy model files into the image
COPY models /models

# Expose the server port
EXPOSE 8087

# Set environment variable
ENV LLAMA_LOG_FORMAT=text

# Run llama.cpp server with granite-docling model
CMD ["-m", "/models/granite-docling-258M-f16.gguf", \
     "--mmproj", "/models/mmproj-granite-docling-258M-f16.gguf", \
     "--host", "0.0.0.0", \
     "--port", "8087", \
     "--n-gpu-layers", "0", \
     "--threads", "6", \
     "--ctx-size", "8192", \
     "--batch-size", "512"]
