#pragma once

#include "data.hpp"

namespace cmc {

template <usize... Indexes>
struct index_sequence {};

template <usize Count, usize... Indexes>
struct make_index_sequence_impl : make_index_sequence_impl<Count - 1U, Count - 1U, Indexes...> {};

template <usize... Indexes>
struct make_index_sequence_impl<0U, Indexes...> {
    using type = index_sequence<Indexes...>;
};

template <usize Count>
using make_index_sequence = typename make_index_sequence_impl<Count>::type;

template <u8... Bytes>
struct byte_string {
    inline static constexpr u8 values[sizeof...(Bytes)] = {Bytes...};
    inline static constexpr usize size = sizeof...(Bytes);

    static constexpr u8 at(usize index) {
        return values[index];
    }
};

template <u8... Bytes>
struct witness_bytes {
    inline static constexpr u8 values[sizeof...(Bytes)] = {Bytes...};
    inline static constexpr usize size = sizeof...(Bytes);

    static constexpr u8 at(usize index) {
        return values[index];
    }
};

constexpr u8 rotl8(u8 value, unsigned int amount) {
    amount &= 7U;
    const auto wide = static_cast<unsigned int>(value);
    return static_cast<u8>(amount == 0U
        ? wide
        : ((wide << amount) | (wide >> (8U - amount))));
}

constexpr u8 rotr8(u8 value, unsigned int amount) {
    amount &= 7U;
    const auto wide = static_cast<unsigned int>(value);
    return static_cast<u8>(amount == 0U
        ? wide
        : ((wide >> amount) | (wide << (8U - amount))));
}

constexpr u32 rotl32(u32 value, unsigned int amount) {
    amount &= 31U;
    return amount == 0U
        ? value
        : static_cast<u32>((value << amount) | (value >> (32U - amount)));
}

constexpr u64 xorshift64(u64 value) {
    value ^= value << 13U;
    value ^= value >> 7U;
    value ^= value << 17U;
    return value;
}

inline constexpr u8 op_halt = 0xd3U;
inline constexpr u8 op_xori = 0x8eU;
inline constexpr u8 op_addi = 0x41U;
inline constexpr u8 op_rotl = 0xb7U;
inline constexpr u8 op_xorr = 0x2cU;
inline constexpr u8 op_addr = 0xf0U;
inline constexpr u8 op_swap = 0x69U;
inline constexpr u8 op_sbox = 0x15U;
inline constexpr u8 op_perm = 0xcaU;
inline constexpr u8 op_mix = 0x73U;
inline constexpr u8 op_muli = 0xa4U;
inline constexpr u8 op_not = 0x5bU;

constexpr u8 checker_opcode_mask(usize step) {
    u32 value = static_cast<u32>(0xa5f1523dU + static_cast<u32>(step) * 0x9e3779b9U);
    value ^= value >> 16U;
    value *= 0x7feb352dU;
    value ^= value >> 15U;
    value *= 0x846ca68bU;
    value ^= value >> 16U;
    return static_cast<u8>(value);
}

constexpr u32 substitute_nibbles(u32 value) {
    u32 result = 0U;
    for (usize shift = 0; shift < 32U; shift += 4U) {
        const auto nibble = static_cast<u8>((value >> shift) & 0xfU);
        result |= static_cast<u32>(data::nibble_sbox[nibble]) << shift;
    }
    return result;
}

constexpr u32 read_program_u32(usize offset) {
    return static_cast<u32>(data::checker_program[offset])
        | (static_cast<u32>(data::checker_program[offset + 1U]) << 8U)
        | (static_cast<u32>(data::checker_program[offset + 2U]) << 16U)
        | (static_cast<u32>(data::checker_program[offset + 3U]) << 24U);
}

template <typename W>
constexpr u32 read_witness_word(usize word_index) {
    const usize offset = word_index * 4U;
    return static_cast<u32>(W::at(offset))
        | (static_cast<u32>(W::at(offset + 1U)) << 8U)
        | (static_cast<u32>(W::at(offset + 2U)) << 16U)
        | (static_cast<u32>(W::at(offset + 3U)) << 24U);
}

template <typename W>
constexpr bool validate_witness() {
    if (W::size != data::witness_size) {
        return false;
    }

    u32 registers[data::checker_register_count] = {};
    for (usize index = 0; index < data::checker_register_count; ++index) {
        registers[index] = read_witness_word<W>(index);
    }

    usize pc = 0U;
    usize steps = 0U;
    bool halted = false;

    while (!halted && pc < data::checker_program_size && steps < 1024U) {
        const u8 encoded_opcode = data::checker_program[pc++];
        const u8 opcode = static_cast<u8>(encoded_opcode ^ checker_opcode_mask(steps));
        ++steps;

        if (opcode == op_halt) {
            halted = true;
        } else if (opcode == op_xori || opcode == op_addi || opcode == op_muli) {
            if (pc + 5U > data::checker_program_size) {
                return false;
            }
            const usize target = data::checker_program[pc++];
            const u32 immediate = read_program_u32(pc);
            pc += 4U;
            if (target >= data::checker_register_count) {
                return false;
            }
            if (opcode == op_xori) {
                registers[target] ^= immediate;
            } else if (opcode == op_addi) {
                registers[target] += immediate;
            } else {
                registers[target] *= immediate;
            }
        } else if (opcode == op_rotl) {
            if (pc + 2U > data::checker_program_size) {
                return false;
            }
            const usize target = data::checker_program[pc++];
            const unsigned int amount = data::checker_program[pc++];
            if (target >= data::checker_register_count) {
                return false;
            }
            registers[target] = rotl32(registers[target], amount);
        } else if (opcode == op_xorr || opcode == op_addr || opcode == op_swap) {
            if (pc + 2U > data::checker_program_size) {
                return false;
            }
            const usize left = data::checker_program[pc++];
            const usize right = data::checker_program[pc++];
            if (left >= data::checker_register_count || right >= data::checker_register_count) {
                return false;
            }
            if (opcode == op_xorr) {
                registers[left] ^= registers[right];
            } else if (opcode == op_addr) {
                registers[left] += registers[right];
            } else {
                const u32 temporary = registers[left];
                registers[left] = registers[right];
                registers[right] = temporary;
            }
        } else if (opcode == op_sbox || opcode == op_not) {
            if (pc + 1U > data::checker_program_size) {
                return false;
            }
            const usize target = data::checker_program[pc++];
            if (target >= data::checker_register_count) {
                return false;
            }
            registers[target] = opcode == op_sbox
                ? substitute_nibbles(registers[target])
                : static_cast<u32>(~registers[target]);
        } else if (opcode == op_perm) {
            if (pc + 1U > data::checker_program_size) {
                return false;
            }
            const usize permutation = data::checker_program[pc++];
            if (permutation >= 4U) {
                return false;
            }
            u32 temporary[data::checker_register_count] = {};
            for (usize index = 0; index < data::checker_register_count; ++index) {
                temporary[index] = registers[data::register_permutations[permutation][index]];
            }
            for (usize index = 0; index < data::checker_register_count; ++index) {
                registers[index] = temporary[index];
            }
        } else if (opcode == op_mix) {
            if (pc + 3U > data::checker_program_size) {
                return false;
            }
            const usize left = data::checker_program[pc++];
            const usize right = data::checker_program[pc++];
            const unsigned int amount = data::checker_program[pc++];
            if (left >= data::checker_register_count || right >= data::checker_register_count) {
                return false;
            }
            registers[left] += rotl32(registers[right], amount);
            registers[right] ^= rotl32(registers[left], amount * 3U + 1U);
        } else {
            return false;
        }
    }

    if (!halted || pc != data::checker_program_size) {
        return false;
    }
    for (usize index = 0; index < data::checker_register_count; ++index) {
        if (registers[index] != data::checker_target[index]) {
            return false;
        }
    }
    return true;
}

template <typename W>
constexpr u64 seed_from_witness() {
    u64 state = 0x9e3779b97f4a7c15ULL;

    for (usize index = 0; index < data::witness_size; ++index) {
        state ^= static_cast<u64>(W::at(index)) << ((index & 7U) * 8U);
        state = xorshift64(state + 0xd1b54a32d192ed03ULL + index);
    }

    return state;
}

template <typename W>
constexpr u8 stream_byte(usize index) {
    u64 state = seed_from_witness<W>()
        ^ (0xa5a5a5a5a5a5a5a5ULL + index * 0x100000001b3ULL);

    for (usize step = 0; step < index + 6U; ++step) {
        state = xorshift64(state + 0x9e3779b97f4a7c15ULL + step);
    }

    return static_cast<u8>(state >> ((index & 7U) * 8U));
}

template <usize Index, typename W>
struct decode_byte {
    inline static constexpr u8 addend = static_cast<u8>(
        0x31U + Index * 0x2dU + W::at((Index + 5U) % data::witness_size));
    inline static constexpr unsigned int rotation = static_cast<unsigned int>(
        (Index * 5U + W::at((Index * 3U + 7U) % data::witness_size)) & 7U);
    inline static constexpr u8 salt = static_cast<u8>(Index * 13U + 0xa7U);
    inline static constexpr u8 mixed = static_cast<u8>(
        data::encrypted[data::permutation[Index]]
        ^ stream_byte<W>(Index)
        ^ W::at((Index * 7U + 11U) % data::witness_size)
        ^ salt);
    inline static constexpr u8 value = static_cast<u8>(
        rotl8(mixed, rotation) - addend);
};

template <typename W, typename Sequence>
struct make_bytes_impl;

template <typename W, usize... Indexes>
struct make_bytes_impl<W, index_sequence<Indexes...>> {
    using type = byte_string<decode_byte<Indexes, W>::value...>;
};

template <typename W>
struct program {
    static_assert(validate_witness<W>(), "generated witness does not satisfy the public constraints");

    using bytes = typename make_bytes_impl<W, make_index_sequence<data::message_size>>::type;
};

} // namespace cmc
