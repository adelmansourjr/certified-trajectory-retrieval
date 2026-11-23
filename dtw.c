#include <math.h>
#include <stdint.h>
#include <stdlib.h>

/* Same exact squared-Euclidean, band-constrained backend for every method. */
double dtw(const double *x, const double *y, int n, int dims, int radius,
           double cutoff, uint64_t *cells) {
    double *a=malloc((n+1)*sizeof(double)), *b=malloc((n+1)*sizeof(double));
    for(int j=0;j<=n;j++) a[j]=INFINITY;
    a[0]=0.;
    for(int i=1;i<=n;i++) {
        for(int j=0;j<=n;j++) b[j]=INFINITY;
        double rowmin=INFINITY;
        int lo=i-radius>1?i-radius:1, hi=i+radius<n?i+radius:n;
        for(int j=lo;j<=hi;j++) {
            double cost=0.;
            for(int k=0;k<dims;k++) {
                double v=x[(i-1)*dims+k]-y[(j-1)*dims+k]; cost+=v*v;
            }
            double v=fmin(a[j],fmin(a[j-1],b[j-1]))+cost;
            b[j]=v; if(v<rowmin) rowmin=v; (*cells)++;
        }
        double *tmp=a;a=b;b=tmp;
        if(rowmin>cutoff) { free(a);free(b);return INFINITY; }
    }
    double result=a[n];free(a);free(b);return result;
}
