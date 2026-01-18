FROM python:3.11-slim

WORKDIR /app

# Set critical environment variables for single-thread stability
ENV KMP_DUPLICATE_LIB_OK=TRUE
ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV DISABLE_MODEL_SOURCE_CHECK=True

RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 libgomp1 wget \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip && \
    pip install paddlepaddle==2.6.1 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/

# Install numpy 1.x compatible with PaddlePaddle
RUN pip install --no-cache-dir "numpy<2.0" opencv-python-headless

RUN pip install --no-cache-dir setuptools wheel cython
RUN pip install --no-cache-dir paddleocr==2.7.3 PyMuPDF fastapi uvicorn python-multipart

# Copy pre-downloaded models into the image
COPY models/whl /root/.paddleocr/whl

#COPY main.py /app/main.py

EXPOSE 8088
# Run with 1 worker
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8088", "--workers", "1"]
