/* Writes tests/fixtures/rules.json from the GBA game's own C rules
 * (squishy-isle rom/src/collection.c and save.c, v1.6). The TypeScript port
 * must give the same rolls, letters, followers and save bytes.
 *
 * Build and run (needs a squishy-isle checkout):
 *   gcc -O2 -I ../squishy-isle/rom/src tests/fixtures/gen_rules.c -o build/gen_rules
 *   ./build/gen_rules > tests/fixtures/rules.json
 */
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include "gba.h"
#undef SRAM
static u8 fake_sram[0x8000];
#define SRAM ((vu8 *)fake_sram)
#include "save.c"
#define HOST_TEST
#include "collection.c"

bool collection_save(void) { return save_store(&game_save); }

static void hex(const char *key, const void *p, int n, const char *end) {
    const u8 *b = p;
    printf("\"%s\":\"", key);
    for (int i = 0; i < n; i++) printf("%02x", b[i]);
    printf("\"%s", end);
}

static u32 lcg = 12345;
static u8 lcg_byte(void) { lcg = lcg * 1103515245u + 12345u; return (u8)(lcg >> 16); }

int main(void) {
    printf("{\"source\":\"squishy-isle 1d99c2e (v1.6) collection.c + save.c\",\"games\":[\n");
    for (u32 s = 1; s <= 50; s++) {
        memset(fake_sram, 0xFF, sizeof fake_sram);
        memset(&game_save, 0, sizeof game_save);
        int st = save_load(&game_save);
        u32 seed = s * 2654435761u;
        collection_new_game(seed);
        printf("{\"n\":%u,\"seed\":%u,\"load\":%d,\"steps\":[", s, seed, st);
        int first = 1;
        for (int area = 0; area < 4; area++) {
            for (int k = 0; k < 20; k++) {
                u32 e = s * 7 + (u32)k * 13;
                int id = collection_roll(area, e);
                bool added = collection_add(id);
                printf("%s{\"a\":%d,\"e\":%u,\"id\":%d,\"ok\":%d", first ? "" : ",", area, e, id, added);
                first = 0;
                if (k % 3 == 2) printf(",\"letter\":%d", letter_open());
                printf("}");
            }
            follower_add(area * 20 + (int)(s % 20));
            follower_remove((int)((s * 3) % 80));
        }
        int full = collection_roll(0, 1);   /* one call per statement: C does not fix the order of printf's arguments */
        u32 r1 = game_rand();
        u32 r2 = game_rand();
        u32 r3 = game_rand();
        printf("],\"full\":%d,\"rand\":[%u,%u,%u],", full, r1, r2, r3);
        hex("save", &game_save, sizeof game_save, ",");
        hex("slot0", fake_sram, sizeof(SaveData), ",");
        hex("slot1", fake_sram + SLOT_SIZE, sizeof(SaveData), "");
        printf("}%s\n", s < 50 ? "," : "");
    }
    printf("],\"sanitize\":[\n");
    for (int s = 0; s < 50; s++) {
        u8 raw[sizeof(SaveData)];
        for (u32 i = 0; i < sizeof raw; i++) raw[i] = lcg_byte();
        if (s % 2) for (int i = 16; i < 96; i++) raw[i] &= 3;      /* half the cases look like real found flags */
        memcpy(&game_save, raw, sizeof raw);
        save_sanitize();
        lines_merge();
        printf("{\"crc\":%u,\"old\":%u,", checksum((SaveData *)raw), checksum_old((SaveData *)raw));
        hex("in", raw, sizeof raw, ",");
        hex("out", &game_save, sizeof game_save, "");
        printf("}%s\n", s < 49 ? "," : "");
    }
    printf("]}\n");
    return 0;
}
