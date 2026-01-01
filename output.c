#include <stdio.h>

int main() {
    int values[4] = {1, 4, 9, 16};
    int total = 0;
    for (int i = 0; i < 4; i++) {
        total = total + values[i];
    }

    printf("%d\n", total);

    return 0;
}