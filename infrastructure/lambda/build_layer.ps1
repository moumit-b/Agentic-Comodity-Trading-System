$ErrorActionPreference = "Stop"

Write-Host "Building Lambda Layer with Docker..."

# Clean up
if (Test-Path python) { Remove-Item -Recurse -Force python }
if (Test-Path layer.zip) { Remove-Item -Force layer.zip }
if (Test-Path Dockerfile.lambda-layer) { Remove-Item -Force Dockerfile.lambda-layer }

# Create Dockerfile
$dockerfile = @'
FROM public.ecr.aws/lambda/python:3.11
RUN yum install -y gcc gcc-c++ make cmake zip unzip postgresql-devel && yum clean all
COPY trading_loop/requirements.txt /tmp/requirements.txt
WORKDIR /tmp
RUN mkdir -p python
RUN pip install --only-binary :all: --target python --upgrade -r requirements.txt --no-cache-dir || \
    pip install --target python --upgrade -r requirements.txt --no-cache-dir
RUN cd python && find . -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
RUN cd python && find . -name "*.pyc" -delete
RUN cd python && find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
RUN cd /tmp && zip -r layer.zip python
CMD ["bash"]
'@

$dockerfile | Out-File -Encoding ASCII Dockerfile.lambda-layer

# Build
Write-Host "Building Docker image..."
docker build -f Dockerfile.lambda-layer -t lambda-layer-builder .

# Extract
Write-Host "Extracting layer..."
$cid = docker create lambda-layer-builder
docker cp "${cid}:/tmp/layer.zip" ./layer.zip
docker cp "${cid}:/tmp/python" ./python
docker rm $cid

$size = (Get-Item layer.zip).Length / 1MB
Write-Host "Build complete! Layer size: $([math]::Round($size, 2)) MB"
