#include "vm.hpp"
#include "generated_witness.hpp"

extern "C" int putchar(int);

int main() {
    using bytes = typename cmc::program<cmc::witness>::bytes;

    for (cmc::usize index = 0; index < bytes::size; ++index) {
        putchar(bytes::at(index));
    }
    putchar('\n');

    return 0;
}
