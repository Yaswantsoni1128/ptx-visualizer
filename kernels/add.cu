#include <cuda_runtime.h>

extern "C" __global__ void add(const int* a, const int* b, int* c, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;

    if (i < n) {
        c[i] = a[i] + b[i];
    }
}

extern "C" __global__ void saxpy(const float* x, const float* y, float* z, float alpha, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;

    if (i < n) {
        z[i] = alpha * x[i] + y[i];
    }
}