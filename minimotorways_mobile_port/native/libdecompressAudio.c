/*
 * libdecompressAudio.c — Clean-room C99 replacement for decompressAudio.dll
 * Targets Android ARM64 (libdecompressAudio.so) and desktop host testing.
 *
 * Implements the two exports required by Mini Motorways (DllUtilities & AudioDataBank):
 *   - int EmptyFunction(void)
 *   - bool decompressAudioSample(
 *         int16_t* decompressedAudio,
 *         int32_t  decompressedOffset,
 *         int32_t  decompressedLength,
 *         int32_t  resampledLength,
 *         int32_t  decompressedSampleRate,
 *         const uint8_t* compressedAudio,
 *         int32_t  compressedOffset,
 *         int32_t  compressedSampleRate)
 *
 * Each entry in StreamingAssets/Sounds/<rate>/core.bytes is a 32-bit little-endian
 * byte length followed immediately by a standard mono 16-bit FLAC stream ("fLaC"...).
 */

#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#if defined(_WIN32)
#define DPC_EXPORT __declspec(dllexport)
#else
#define DPC_EXPORT __attribute__((visibility("default")))
#endif

DPC_EXPORT int EmptyFunction(void) {
    return 0;
}

DPC_EXPORT void setLogDelegate(void* callback) {
    (void)callback;
}

typedef struct {
    const uint8_t* data;
    size_t size;
    size_t byte_pos;
    uint32_t bit_Pos; /* 0..7 within current byte */
    bool eof;
} BitReader;

static void br_init(BitReader* br, const uint8_t* data, size_t size) {
    br->data = data;
    br->size = size;
    br->byte_pos = 0;
    br->bit_Pos = 0;
    br->eof = false;
}

static uint64_t br_read_uint(BitReader* br, int bits) {
    uint64_t result = 0;
    while (bits > 0) {
        if (br->byte_pos >= br->size) {
            br->eof = true;
            return 0;
        }
        int avail = 8 - (int)br->bit_Pos;
        int take = bits < avail ? bits : avail;
        uint8_t cur = br->data[br->byte_pos];
        uint8_t shift = (uint8_t)(avail - take);
        uint8_t mask = (uint8_t)(((1u << take) - 1u) << shift);
        result = (result << take) | (uint64_t)((cur & mask) >> shift);
        br->bit_Pos += (uint32_t)take;
        if (br->bit_Pos == 8) {
            br->bit_Pos = 0;
            br->byte_pos++;
        }
        bits -= take;
    }
    return result;
}

static int64_t br_read_sint(BitReader* br, int bits) {
    if (bits <= 0) return 0;
    uint64_t u = br_read_uint(br, bits);
    uint64_t sign_bit = 1ULL << (bits - 1);
    if (u & sign_bit) {
        return (int64_t)(u | (~0ULL << bits));
    }
    return (int64_t)u;
}

static uint32_t br_read_unary(BitReader* br) {
    uint32_t zeros = 0;
    while (!br->eof) {
        if (br->byte_pos >= br->size) {
            br->eof = true;
            return zeros;
        }
        uint8_t cur = br->data[br->byte_pos];
        int bit = (cur >> (7 - br->bit_Pos)) & 1;
        br->bit_Pos++;
        if (br->bit_Pos == 8) {
            br->bit_Pos = 0;
            br->byte_pos++;
        }
        if (bit == 1) {
            return zeros;
        }
        zeros++;
        if (zeros > 0x100000u) {
            br->eof = true;
            return zeros;
        }
    }
    return zeros;
}

static void br_align_byte(BitReader* br) {
    if (br->bit_Pos != 0) {
        br->bit_Pos = 0;
        br->byte_pos++;
    }
}

static bool skip_utf8_number(BitReader* br) {
    uint32_t first = (uint32_t)br_read_uint(br, 8);
    if (br->eof) return false;
    if ((first & 0x80u) == 0) return true;
    int extra = 0;
    if ((first & 0xE0u) == 0xC0u) extra = 1;
    else if ((first & 0xF0u) == 0xE0u) extra = 2;
    else if ((first & 0xF8u) == 0xF0u) extra = 3;
    else if ((first & 0xFCu) == 0xF8u) extra = 4;
    else if ((first & 0xFEu) == 0xFCu) extra = 5;
    else if (first == 0xFEu) extra = 6;
    else return false;
    for (int i = 0; i < extra; i++) {
        uint32_t b = (uint32_t)br_read_uint(br, 8);
        if (br->eof || (b & 0xC0u) != 0x80u) return false;
    }
    return true;
}

static bool decode_residuals(BitReader* br, int32_t* buf, int block_size, int pred_order) {
    uint32_t method = (uint32_t)br_read_uint(br, 2);
    if (method > 1) return false;
    int param_bits = (method == 0) ? 4 : 5;
    uint32_t escape_param = (method == 0) ? 15u : 31u;
    int part_order = (int)br_read_uint(br, 4);
    int num_parts = 1 << part_order;
    if ((block_size % num_parts) != 0) return false;
    int part_samples = block_size >> part_order;

    int sample_idx = pred_order;
    for (int p = 0; p < num_parts; p++) {
        uint32_t rice_param = (uint32_t)br_read_uint(br, param_bits);
        int count = (p == 0) ? (part_samples - pred_order) : part_samples;
        if (count < 0 || sample_idx + count > block_size) return false;
        if (rice_param == escape_param) {
            int raw_bits = (int)br_read_uint(br, 5);
            for (int i = 0; i < count; i++) {
                buf[sample_idx++] = (raw_bits == 0) ? 0 : (int32_t)br_read_sint(br, raw_bits);
            }
        } else {
            for (int i = 0; i < count; i++) {
                uint32_t q = br_read_unary(br);
                uint32_t rem = (rice_param == 0) ? 0u : (uint32_t)br_read_uint(br, (int)rice_param);
                uint32_t u = (q << rice_param) | rem;
                int32_t val = (int32_t)((u >> 1) ^ (uint32_t)(-(int32_t)(u & 1u)));
                buf[sample_idx++] = val;
            }
        }
        if (br->eof) return false;
    }
    return true;
}

static bool decode_subframe(BitReader* br, int32_t* buf, int block_size, int bps) {
    uint32_t zero_bit = (uint32_t)br_read_uint(br, 1);
    if (zero_bit != 0) return false;
    uint32_t type_code = (uint32_t)br_read_uint(br, 6);
    uint32_t has_wasted = (uint32_t)br_read_uint(br, 1);
    int wasted = 0;
    if (has_wasted) {
        wasted = (int)br_read_unary(br) + 1;
    }
    int sub_bps = bps - wasted;
    if (sub_bps <= 0 || sub_bps > 32) return false;

    if (type_code == 0) {
        /* SUBFRAME_CONSTANT */
        int32_t c = (int32_t)br_read_sint(br, sub_bps);
        for (int i = 0; i < block_size; i++) buf[i] = c;
    } else if (type_code == 1) {
        /* SUBFRAME_VERBATIM */
        for (int i = 0; i < block_size; i++) {
            buf[i] = (int32_t)br_read_sint(br, sub_bps);
        }
    } else if (type_code >= 8 && type_code <= 12) {
        /* SUBFRAME_FIXED */
        int order = (int)(type_code & 7u);
        if (order > block_size) return false;
        for (int i = 0; i < order; i++) {
            buf[i] = (int32_t)br_read_sint(br, sub_bps);
        }
        if (!decode_residuals(br, buf, block_size, order)) return false;
        switch (order) {
            case 0:
                break;
            case 1:
                for (int i = 1; i < block_size; i++) {
                    buf[i] += buf[i - 1];
                }
                break;
            case 2:
                for (int i = 2; i < block_size; i++) {
                    buf[i] += (int32_t)(2LL * buf[i - 1] - buf[i - 2]);
                }
                break;
            case 3:
                for (int i = 3; i < block_size; i++) {
                    buf[i] += (int32_t)(3LL * buf[i - 1] - 3LL * buf[i - 2] + buf[i - 3]);
                }
                break;
            case 4:
                for (int i = 4; i < block_size; i++) {
                    buf[i] += (int32_t)(4LL * buf[i - 1] - 6LL * buf[i - 2] + 4LL * buf[i - 3] - buf[i - 4]);
                }
                break;
        }
    } else if (type_code >= 32) {
        /* SUBFRAME_LPC */
        int order = (int)(type_code & 31u) + 1;
        if (order > block_size) return false;
        for (int i = 0; i < order; i++) {
            buf[i] = (int32_t)br_read_sint(br, sub_bps);
        }
        int prec = (int)br_read_uint(br, 4) + 1;
        if (prec == 16) return false;
        int shift = (int)br_read_sint(br, 5);
        if (shift < 0) shift = 0;
        int32_t coeffs[32];
        for (int i = 0; i < order; i++) {
            coeffs[i] = (int32_t)br_read_sint(br, prec);
        }
        if (!decode_residuals(br, buf, block_size, order)) return false;
        for (int i = order; i < block_size; i++) {
            int64_t sum = 0;
            for (int j = 0; j < order; j++) {
                sum += (int64_t)coeffs[j] * (int64_t)buf[i - 1 - j];
            }
            buf[i] += (int32_t)(sum >> shift);
        }
    } else {
        return false;
    }

    if (wasted > 0) {
        for (int i = 0; i < block_size; i++) {
            buf[i] = (int32_t)((uint32_t)buf[i] << wasted);
        }
    }
    return !br->eof;
}

DPC_EXPORT bool decompressAudioSample(
    int16_t* decompressedAudio,
    int32_t decompressedOffset,
    int32_t decompressedLength,
    int32_t resampledLength,
    int32_t decompressedSampleRate,
    const uint8_t* compressedAudio,
    int32_t compressedOffset,
    int32_t compressedSampleRate)
{
    (void)decompressedSampleRate;
    (void)compressedSampleRate;

    if (!decompressedAudio || !compressedAudio || decompressedLength <= 0 || resampledLength <= 0) {
        return false;
    }
    if (resampledLength != decompressedLength && resampledLength != decompressedLength * 2) {
        return false;
    }

    const uint8_t* entry = compressedAudio + compressedOffset;
    uint32_t flac_size = (uint32_t)entry[0]
                       | ((uint32_t)entry[1] << 8)
                       | ((uint32_t)entry[2] << 16)
                       | ((uint32_t)entry[3] << 24);
    const uint8_t* flac_data = entry + 4;

    if (flac_size < 42 || memcmp(flac_data, "fLaC", 4) != 0) {
        return false;
    }

    size_t pos = 4;
    int stream_bps = 16;
    int stream_channels = 1;
    while (pos + 4 <= flac_size) {
        uint8_t header = flac_data[pos];
        bool is_last = (header & 0x80u) != 0;
        uint8_t block_type = header & 0x7Fu;
        uint32_t block_len = ((uint32_t)flac_data[pos + 1] << 16)
                           | ((uint32_t)flac_data[pos + 2] << 8)
                           | (uint32_t)flac_data[pos + 3];
        pos += 4;
        if (pos + block_len > flac_size) return false;
        if (block_type == 0 && block_len >= 18) {
            /* STREAMINFO */
            uint8_t b12 = flac_data[pos + 12];
            uint8_t b13 = flac_data[pos + 13];
            stream_channels = ((b12 >> 1) & 0x7) + 1;
            stream_bps = (((b12 & 1) << 4) | (b13 >> 4)) + 1;
        }
        pos += block_len;
        if (is_last) break;
    }

    int16_t* out_base = (int16_t*)((uint8_t*)decompressedAudio + decompressedOffset);
    int16_t* decode_target = out_base;
    if (resampledLength == decompressedLength * 2) {
        decode_target = (int16_t*)malloc((size_t)decompressedLength * sizeof(int16_t));
        if (!decode_target) return false;
    }

    int32_t* block_buf = (int32_t*)malloc(65536 * sizeof(int32_t));
    int32_t* ch1_buf = (stream_channels > 1) ? (int32_t*)malloc(65536 * sizeof(int32_t)) : NULL;
    if (!block_buf || (stream_channels > 1 && !ch1_buf)) {
        free(decode_target != out_base ? decode_target : NULL);
        free(block_buf);
        free(ch1_buf);
        return false;
    }

    BitReader br;
    br_init(&br, flac_data + pos, flac_size - pos);

    int32_t written = 0;
    bool ok = true;
    while (written < decompressedLength && br.byte_pos < br.size) {
        uint32_t sync = (uint32_t)br_read_uint(&br, 14);
        if (br.eof) break;
        if (sync != 0x3FFEu) {
            ok = false;
            break;
        }
        uint32_t reserved1 = (uint32_t)br_read_uint(&br, 1);
        uint32_t blocking_strategy = (uint32_t)br_read_uint(&br, 1);
        (void)reserved1;
        (void)blocking_strategy;

        uint32_t bs_code = (uint32_t)br_read_uint(&br, 4);
        uint32_t sr_code = (uint32_t)br_read_uint(&br, 4);
        uint32_t ch_assign = (uint32_t)br_read_uint(&br, 4);
        uint32_t ss_code = (uint32_t)br_read_uint(&br, 3);
        uint32_t reserved2 = (uint32_t)br_read_uint(&br, 1);
        (void)reserved2;

        if (!skip_utf8_number(&br)) {
            ok = false;
            break;
        }

        int block_size = 0;
        if (bs_code == 1) block_size = 192;
        else if (bs_code >= 2 && bs_code <= 5) block_size = 576 << (bs_code - 2);
        else if (bs_code == 6) block_size = (int)br_read_uint(&br, 8) + 1;
        else if (bs_code == 7) block_size = (int)br_read_uint(&br, 16) + 1;
        else if (bs_code >= 8 && bs_code <= 15) block_size = 256 << (bs_code - 8);
        else { ok = false; break; }

        if (sr_code == 12) (void)br_read_uint(&br, 8);
        else if (sr_code == 13 || sr_code == 14) (void)br_read_uint(&br, 16);

        /* Frame header CRC-8 */
        (void)br_read_uint(&br, 8);

        int bps = stream_bps;
        if (ss_code == 1) bps = 8;
        else if (ss_code == 2) bps = 12;
        else if (ss_code == 4) bps = 16;
        else if (ss_code == 5) bps = 20;
        else if (ss_code == 6) bps = 24;

        if (ch_assign == 0) {
            if (!decode_subframe(&br, block_buf, block_size, bps)) {
                ok = false;
                break;
            }
        } else if (ch_assign >= 1 && ch_assign <= 10 && ch1_buf != NULL) {
            int bps0 = bps + ((ch_assign == 9) ? 1 : 0);
            int bps1 = bps + ((ch_assign == 8 || ch_assign == 10) ? 1 : 0);
            if (!decode_subframe(&br, block_buf, block_size, bps0) ||
                !decode_subframe(&br, ch1_buf, block_size, bps1)) {
                ok = false;
                break;
            }
        } else {
            ok = false;
            break;
        }

        br_align_byte(&br);
        /* Frame footer CRC-16 */
        (void)br_read_uint(&br, 16);

        int to_copy = block_size;
        if (written + to_copy > decompressedLength) {
            to_copy = decompressedLength - written;
        }
        for (int i = 0; i < to_copy; i++) {
            int32_t s = block_buf[i];
            if (s > 32767) s = 32767;
            else if (s < -32768) s = -32768;
            decode_target[written + i] = (int16_t)s;
        }
        written += to_copy;
    }

    if (ok && written < decompressedLength) {
        memset(decode_target + written, 0, (size_t)(decompressedLength - written) * sizeof(int16_t));
    }

    if (decode_target != out_base) {
        if (ok) {
            for (int32_t i = 0; i < decompressedLength; i++) {
                int16_t s = decode_target[i];
                out_base[i * 2] = s;
                out_base[i * 2 + 1] = s;
            }
        }
        free(decode_target);
    }

    free(block_buf);
    free(ch1_buf);
    return ok;
}

#if defined(__ANDROID__)
#include <jni.h>

JNIEXPORT jboolean JNICALL
Java_com_dinopoloclub_minimotorways_MobilePortActivity_nativeDecompressFlac(
    JNIEnv* env,
    jclass clazz,
    jbyteArray compressedBank,
    jint compressedOffset,
    jshortArray decompressedOut,
    jint sampleCount)
{
    (void)clazz;
    if (!compressedBank || !decompressedOut || sampleCount <= 0) return JNI_FALSE;
    jbyte* bankPtr = (*env)->GetByteArrayElements(env, compressedBank, NULL);
    jshort* outPtr = (*env)->GetShortArrayElements(env, decompressedOut, NULL);
    bool ok = false;
    if (bankPtr && outPtr) {
        ok = decompressAudioSample(
            (int16_t*)outPtr, 0, (int32_t)sampleCount, (int32_t)sampleCount,
            48000, (const uint8_t*)bankPtr, (int32_t)compressedOffset, 48000);
    }
    if (bankPtr) (*env)->ReleaseByteArrayElements(env, compressedBank, bankPtr, JNI_ABORT);
    if (outPtr) (*env)->ReleaseShortArrayElements(env, decompressedOut, outPtr, 0);
    return ok ? JNI_TRUE : JNI_FALSE;
}
#endif

