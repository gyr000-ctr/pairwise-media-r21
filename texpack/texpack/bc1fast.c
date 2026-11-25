/*
 * bc1fast.c — texpack 的可选原生加速（标量/灰度 4x4 块）。
 *
 * 16 个 double 进，8 字节（打包成 u64）出。形状/有限性校验与错误分类仍在
 * Python 侧；本文件不依赖 Python ABI，可用任意 C 编译器构建后由 ctypes 加载。
 *
 * 端点选择（最小二乘，而非取极值）：一维情形下最优 4 级标注在排序后必为
 * 4 个连续组，因此枚举 C(15,3)=455 个切分，对每种切分用前缀和 O(1) 求解
 * y = b + h*j 的 2x2 最小二乘（BC1 的 4 个等距调色板层级），保留 LS 误差
 * 最小的若干候选，再在真实 RGB565 线调色板上做精确 SSE 与绿码 ±1 选码。
 * 无全局可变状态，可并发调用。
 */

#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#ifdef _WIN32
#  define EXPORT __declspec(dllexport)
#else
#  define EXPORT __attribute__((visibility("default")))
#endif

static int pack_gray(double y) {
    if (y <= 0.0) y = 0.0;
    else if (y >= 1.0) y = 1.0;
    int r = (int)(y * 31.0 + 0.5);
    int g = (int)(y * 63.0 + 0.5);
    return (r << 11) | (g << 5) | r;
}

/* 按真实 BC1 绿通道调色板阈值分配并打包 2-bit 索引，返回 SSE */
static double assign_pack(const double *v, int c0, int c1, unsigned *bits) {
    int g0 = (c0 >> 5) & 63, g1 = (c1 >> 5) & 63;
    int G0 = (g0 << 2) | (g0 >> 4), G1 = (g1 << 2) | (g1 >> 4);
    double p0, p1, p2, p3;
    if (c0 > c1) {
        p0 = G0 / 255.0; p1 = G1 / 255.0;
        p2 = ((2 * G0 + G1) / 3) / 255.0;
        p3 = ((G0 + 2 * G1) / 3) / 255.0;
    } else {
        p0 = G0 / 255.0; p1 = G1 / 255.0;
        p2 = ((G0 + G1) / 2) / 255.0; p3 = 0.0;
    }
    double t1 = (p1 + p3) * 0.5;
    double t2 = (p3 + p2) * 0.5;
    double t3 = (p2 + p0) * 0.5;
    unsigned b = 0;
    double sse = 0.0;
    for (int i = 0; i < 16; i++) {
        double x = v[i], p;
        int k;
        if      (x < t1) { k = 1; p = p1; }
        else if (x < t2) { k = 3; p = p3; }
        else if (x < t3) { k = 2; p = p2; }
        else             { k = 0; p = p0; }
        double d = x - p;
        sse += d * d;
        b |= ((unsigned)k) << (2 * i);
    }
    *bits = b;
    return sse;
}

/* 候选 LS 解（截距 b 与步长 h）的小型 top-K */
#define TOPK 8

EXPORT unsigned long long bc1_encode_gray_u64(const double *v) {
    unsigned char out[8];

    double mn = v[0], mx = v[0];
    int all_equal = 1;
    for (int i = 1; i < 16; i++) {
        if (v[i] < mn) mn = v[i];
        if (v[i] > mx) mx = v[i];
        if (v[i] != v[0]) all_equal = 0;
    }
    if (all_equal || mn == mx) {
        int c = pack_gray(v[0]);
        out[0] = (unsigned char)(c & 255);
        out[1] = (unsigned char)(c >> 8);
        out[2] = out[0]; out[3] = out[1];
        out[4] = out[5] = out[6] = out[7] = 0;
        unsigned long long w = 0;
        for (int i = 7; i >= 0; i--) w = (w << 8) | out[i];
        return w;
    }

    double x[16];
    memcpy(x, v, sizeof(x));
    /* 插入排序（n=16，避免 qsort 回调开销） */
    for (int i = 1; i < 16; i++) {
        double key = x[i];
        int j = i - 1;
        while (j >= 0 && x[j] > key) { x[j + 1] = x[j]; j--; }
        x[j + 1] = key;
    }
    double ps[17];
    ps[0] = 0.0;
    double Syy = 0.0;
    for (int i = 0; i < 16; i++) { ps[i + 1] = ps[i] + x[i]; Syy += x[i] * x[i]; }
    double Sy = ps[16];

    double tc[TOPK], tb[TOPK], th[TOPK];
    for (int k = 0; k < TOPK; k++) tc[k] = 1e300;

    /* 三个切分点 a<b<c：组为 [0,a) j=0, [a,b) j=1, [b,c) j=2, [c,16) j=3 */
    for (int a = 1; a <= 13; a++) {
        for (int bnd = a + 1; bnd <= 14; bnd++) {
            for (int c = bnd + 1; c <= 15; c++) {
                double n1 = bnd - a, n2 = c - bnd, n3 = 16 - c;
                double g1 = ps[bnd] - ps[a];
                double g2 = ps[c] - ps[bnd];
                double g3 = ps[16] - ps[c];
                double Sj = n1 + 2.0 * n2 + 3.0 * n3;
                double Sjj = n1 + 4.0 * n2 + 9.0 * n3;
                double Sjy = g1 + 2.0 * g2 + 3.0 * g3;
                double det = 16.0 * Sjj - Sj * Sj;
                if (det < 1e-12) continue;
                double invdet = 1.0 / det;
                double h = (16.0 * Sjy - Sj * Sy) * invdet;
                double bb = (Sy * Sjj - Sj * Sjy) * invdet;
                if (h < 0.0) h = 0.0;
                double cost = Syy - bb * Sy - h * Sjy;
                if (cost < 0.0) cost = 0.0;
                if (cost < tc[TOPK - 1]) {
                    int p = TOPK - 1;
                    while (p > 0 && cost < tc[p - 1]) {
                        tc[p] = tc[p - 1]; tb[p] = tb[p - 1]; th[p] = th[p - 1];
                        p--;
                    }
                    tc[p] = cost; tb[p] = bb; th[p] = h;
                }
            }
        }
    }

    int best_c0 = pack_gray(mx), best_c1 = pack_gray(mn);
    if (best_c0 < best_c1) { int t = best_c0; best_c0 = best_c1; best_c1 = t; }
    unsigned best_bits = 0;
    double best_sse = assign_pack(v, best_c0, best_c1, &best_bits);

    /* 评估 top-K LS 端点对的真实线 SSE */
    int codes0[TOPK + 2], codes1[TOPK + 2];
    int ncand = 0;
    codes0[ncand] = best_c0; codes1[ncand] = best_c1; ncand++;
    for (int k = 0; k < TOPK; k++) {
        if (tc[k] >= 1e299) continue;
        double lo = tb[k];
        double hi = tb[k] + 3.0 * th[k];
        int c0 = pack_gray(hi), c1 = pack_gray(lo);
        if (c0 < c1) { int t = c0; c0 = c1; c1 = t; }
        int dup = 0;
        for (int i = 0; i < ncand; i++)
            if (codes0[i] == c0 && codes1[i] == c1) { dup = 1; break; }
        if (!dup && ncand < TOPK + 2) { codes0[ncand] = c0; codes1[ncand] = c1; ncand++; }
        unsigned bits;
        double sse = assign_pack(v, c0, c1, &bits);
        if (sse < best_sse) {
            best_sse = sse; best_c0 = c0; best_c1 = c1; best_bits = bits;
        }
    }

    /* 围绕当前最优码做绿通道 ±1 邻域精修（按真实 SSE 选择） */
    int g0 = (best_c0 >> 5) & 63, g1 = (best_c1 >> 5) & 63;
    int r0 = (best_c0 >> 11) & 31, b0 = best_c0 & 31;
    int r1 = (best_c1 >> 11) & 31, b1 = best_c1 & 31;
    for (int dg0 = -2; dg0 <= 2; dg0++) {
        int x0 = g0 + dg0;
        if (x0 < 0 || x0 > 63) continue;
        for (int dg1 = -2; dg1 <= 2; dg1++) {
            int x1 = g1 + dg1;
            if (x1 < 0 || x1 > 63 || x1 > x0) continue;
            int c0 = (r0 << 11) | (x0 << 5) | b0;
            int c1 = (r1 << 11) | (x1 << 5) | b1;
            unsigned bits;
            double sse = assign_pack(v, c0, c1, &bits);
            if (sse < best_sse) {
                best_sse = sse; best_c0 = c0; best_c1 = c1; best_bits = bits;
            }
        }
    }

    out[0] = (unsigned char)(best_c0 & 255);
    out[1] = (unsigned char)(best_c0 >> 8);
    out[2] = (unsigned char)(best_c1 & 255);
    out[3] = (unsigned char)(best_c1 >> 8);
    out[4] = (unsigned char)(best_bits & 255);
    out[5] = (unsigned char)((best_bits >> 8) & 255);
    out[6] = (unsigned char)((best_bits >> 16) & 255);
    out[7] = (unsigned char)((best_bits >> 24) & 255);

    unsigned long long w = 0;
    for (int i = 7; i >= 0; i--) w = (w << 8) | out[i];
    return w;
}
