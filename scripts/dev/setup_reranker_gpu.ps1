param(
    [string]$TorchVersion = '2.14.0',
    [string]$CudaChannel = 'cu126'
)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$taskCpuPython = Join-Path $taskRoot '.venv/Scripts/python.exe'
$taskRuntime = Join-Path $taskRoot '.tmp/reranker-gpu-runtime'
if (!(Test-Path -LiteralPath $taskCpuPython -PathType Leaf)) {
    throw 'The project .venv is required before GPU setup.'
}
if ($TorchVersion -notmatch '^2\.\d+\.\d+$' -or $CudaChannel -notmatch '^cu\d+$') {
    throw 'Explicit numeric PyTorch version and CUDA wheel channel required.'
}
if (!(Test-Path -LiteralPath (Join-Path $taskRuntime 'Scripts/python.exe'))) {
    & $taskCpuPython -m venv --system-site-packages $taskRuntime
    if ($LASTEXITCODE -ne 0) { throw 'GPU runtime creation failed.' }
}
$taskGpuPython = Join-Path $taskRuntime 'Scripts/python.exe'
$taskDependencies = @(
    (Join-Path $taskRoot '.venv/Lib/site-packages'),
    (Join-Path $taskRoot 'src')
)
[IO.File]::WriteAllText(
    (Join-Path $taskRuntime 'Lib/site-packages/reranker_local_dependencies.pth'),
    ($taskDependencies -join "`n") + "`n",
    [Text.UTF8Encoding]::new($false)
)
& $taskGpuPython -m pip install --no-deps --index-url "https://download.pytorch.org/whl/$CudaChannel" --cache-dir (Join-Path $taskRoot '.tmp/pip-cache') "torch==$TorchVersion"
if ($LASTEXITCODE -ne 0) { throw 'CUDA wheel installation failed.' }
& $taskGpuPython -c "import torch; assert torch.cuda.is_available(), 'CUDA unavailable'; print({'torch':torch.__version__,'cuda':torch.version.cuda,'gpu':torch.cuda.get_device_name(0)})"
if ($LASTEXITCODE -ne 0) { throw 'GPU activation failed; the CPU .venv remains usable.' }
