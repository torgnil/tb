/*
 * Copyright 2026 Torbjörn Nilsson
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>

#include <raylib.h>

#define TB_RAYLIB_MAX_TEXTURES 256
#define TB_RAYLIB_MAX_SOUNDS 256
#define TB_RAYLIB_MAX_FONTS 32

static Font tb_raylib_fonts[TB_RAYLIB_MAX_FONTS];

static Texture2D tb_raylib_textures[TB_RAYLIB_MAX_TEXTURES];
static bool tb_raylib_texture_used[TB_RAYLIB_MAX_TEXTURES];
static Sound tb_raylib_sounds[TB_RAYLIB_MAX_SOUNDS];
static bool tb_raylib_sound_used[TB_RAYLIB_MAX_SOUNDS];

static Color tb_raylib_color_from_id(int64_t color_id) {
    if (color_id == 0) {
        return BLACK;
    }
    if (color_id == 1) {
        return WHITE;
    }
    if (color_id == 2) {
        return RED;
    }
    if (color_id == 3) {
        return GREEN;
    }
    if (color_id == 4) {
        return BLUE;
    }
    if (color_id == 5) {
        return YELLOW;
    }
    if (color_id == 6) {
        return RAYWHITE;
    }
    if (color_id == 7) {
        return LIGHTGRAY;
    }
    if (color_id == 8) {
        return DARKGRAY;
    }
    return RAYWHITE;
}

static int64_t tb_raylib_store_texture(Texture2D texture) {
    for (int64_t index = 0; index < TB_RAYLIB_MAX_TEXTURES; index++) {
        if (!tb_raylib_texture_used[index]) {
            tb_raylib_texture_used[index] = true;
            tb_raylib_textures[index] = texture;
            return index + 1;
        }
    }
    UnloadTexture(texture);
    return 0;
}

static Texture2D *tb_raylib_texture_from_handle(int64_t handle) {
    if (handle <= 0 || handle > TB_RAYLIB_MAX_TEXTURES) {
        return NULL;
    }
    int64_t index = handle - 1;
    if (!tb_raylib_texture_used[index]) {
        return NULL;
    }
    return &tb_raylib_textures[index];
}

static int64_t tb_raylib_store_sound(Sound sound) {
    for (int64_t index = 0; index < TB_RAYLIB_MAX_SOUNDS; index++) {
        if (!tb_raylib_sound_used[index]) {
            tb_raylib_sound_used[index] = true;
            tb_raylib_sounds[index] = sound;
            return index + 1;
        }
    }
    UnloadSound(sound);
    return 0;
}

static Sound *tb_raylib_sound_from_handle(int64_t handle) {
    if (handle <= 0 || handle > TB_RAYLIB_MAX_SOUNDS) {
        return NULL;
    }
    int64_t index = handle - 1;
    if (!tb_raylib_sound_used[index]) {
        return NULL;
    }
    return &tb_raylib_sounds[index];
}

void __tb_foreign_raylib_EnableResizableWindow(void) {
    SetConfigFlags(FLAG_WINDOW_RESIZABLE);
}

void __tb_foreign_raylib_MaximizeWindow(void) {
    MaximizeWindow();
}

void __tb_foreign_raylib_InitWindow(int64_t width, int64_t height, const char *title) {
    InitWindow((int) width, (int) height, title);
}

bool __tb_foreign_raylib_WindowShouldClose(void) {
    return WindowShouldClose();
}

int64_t __tb_foreign_raylib_GetFrameTimeMillis(void) {
    return (int64_t) (GetFrameTime()*1000.0f);
}

int64_t __tb_foreign_raylib_GetTimeMillis(void) {
    return (int64_t) (GetTime()*1000.0);
}

void __tb_foreign_raylib_SetTargetFPS(int64_t fps) {
    SetTargetFPS((int) fps);
}

void __tb_foreign_raylib_BeginDrawing(void) {
    BeginDrawing();
}

void __tb_foreign_raylib_EndDrawing(void) {
    EndDrawing();
}

void __tb_foreign_raylib_ClearBackground(int64_t color_id) {
    ClearBackground(tb_raylib_color_from_id(color_id));
}

int64_t __tb_foreign_raylib_LoadTexture(const char *path) {
    Texture2D texture = LoadTexture(path);
    if (texture.id == 0) {
        return 0;
    }
    return tb_raylib_store_texture(texture);
}

int64_t __tb_foreign_raylib_LoadFont(const char *path, int64_t font_size) {
    if (font_size < 1 || font_size > INT32_MAX || !FileExists(path)) {
        return 0;
    }
    int codepoints[95 + 224];
    for (int i = 0; i < 95; i++) {
        codepoints[i] = 32 + i;
    }
    for (int i = 0; i < 224; i++) {
        codepoints[95 + i] = 0xa0 + i;
    }
    Font font = LoadFontEx(path, (int) font_size, codepoints, 95 + 224);
    if (font.texture.id == 0 || font.texture.id == GetFontDefault().texture.id) {
        return 0;
    }
    for (int64_t index = 0; index < TB_RAYLIB_MAX_FONTS; index++) {
        if (tb_raylib_fonts[index].texture.id == 0) {
            tb_raylib_fonts[index] = font;
            return index + 1;
        }
    }
    UnloadFont(font);
    return 0;
}

static Font *tb_raylib_font_from_handle(int64_t handle) {
    if (handle <= 0 || handle > TB_RAYLIB_MAX_FONTS ||
        tb_raylib_fonts[handle - 1].texture.id == 0) {
        return NULL;
    }
    return &tb_raylib_fonts[handle - 1];
}

void __tb_foreign_raylib_DrawTextEx(int64_t handle, const char *text, int64_t x, int64_t y,
                                  int64_t font_size, int64_t color_id) {
    Color color = tb_raylib_color_from_id(color_id);
    Font *font = tb_raylib_font_from_handle(handle);
    if (font == NULL) {
        DrawText(text, (int) x, (int) y, (int) font_size, color);
        return;
    }
    Vector2 position = {(float) x, (float) y};
    DrawTextEx(*font, text, position, (float) font_size, 0.0f, color);
}

int64_t __tb_foreign_raylib_MeasureTextWidth(int64_t handle, const char *text, int64_t font_size) {
    Font *font = tb_raylib_font_from_handle(handle);
    if (font == NULL) {
        return MeasureText(text, (int) font_size);
    }
    float width = MeasureTextEx(*font, text, (float) font_size, 0.0f).x;
    return (int64_t) width + (width > (float) (int64_t) width);
}

void __tb_foreign_raylib_DrawTextClipped(int64_t handle, const char *text, int64_t x, int64_t y,
                                       int64_t font_size, int64_t color_id, int64_t width,
                                       int64_t scroll_x) {
    if (width <= 0) {
        return;
    }
    BeginScissorMode((int) x, (int) y - 1, (int) width, (int) font_size + 3);
    __tb_foreign_raylib_DrawTextEx(handle, text, x - scroll_x, y, font_size, color_id);
    EndScissorMode();
}

void __tb_foreign_raylib_UnloadFont(int64_t handle) {
    if (handle > 0 && handle <= TB_RAYLIB_MAX_FONTS &&
        tb_raylib_fonts[handle - 1].texture.id != 0) {
        UnloadFont(tb_raylib_fonts[handle - 1]);
        tb_raylib_fonts[handle - 1] = (Font) {0};
    }
}

void __tb_foreign_raylib_DrawText(const char *text, int64_t x, int64_t y, int64_t font_size, int64_t color_id) {
    DrawText(text, (int) x, (int) y, (int) font_size, tb_raylib_color_from_id(color_id));
}

void __tb_foreign_raylib_DrawTexture(int64_t texture_handle, int64_t x, int64_t y, int64_t color_id) {
    Texture2D *texture = tb_raylib_texture_from_handle(texture_handle);
    if (texture == NULL) {
        return;
    }
    DrawTexture(*texture, (int) x, (int) y, tb_raylib_color_from_id(color_id));
}

void __tb_foreign_raylib_DrawTextureSized(int64_t handle, int64_t x, int64_t y,
                                        int64_t width, int64_t height, int64_t color_id) {
    Texture2D *texture = tb_raylib_texture_from_handle(handle);
    if (texture == NULL || width <= 0 || height <= 0) {
        return;
    }
    Rectangle source = {0.0f, 0.0f, (float) texture->width, (float) texture->height};
    Rectangle destination = {(float) x, (float) y, (float) width, (float) height};
    DrawTexturePro(*texture, source, destination, (Vector2) {0.0f, 0.0f}, 0.0f,
                   tb_raylib_color_from_id(color_id));
}

void __tb_foreign_raylib_UnloadTexture(int64_t texture_handle) {
    Texture2D *texture = tb_raylib_texture_from_handle(texture_handle);
    if (texture == NULL) {
        return;
    }
    int64_t index = texture_handle - 1;
    UnloadTexture(*texture);
    tb_raylib_texture_used[index] = false;
    tb_raylib_textures[index] = (Texture2D) {0};
}

void __tb_foreign_raylib_DrawRectangle(int64_t x, int64_t y, int64_t width, int64_t height, int64_t color_id) {
    DrawRectangle((int) x, (int) y, (int) width, (int) height, tb_raylib_color_from_id(color_id));
}

void __tb_foreign_raylib_DrawCircle(int64_t center_x, int64_t center_y, int64_t radius, int64_t color_id) {
    DrawCircle((int) center_x, (int) center_y, (float) radius, tb_raylib_color_from_id(color_id));
}

void __tb_foreign_raylib_DrawLine(int64_t start_x, int64_t start_y, int64_t end_x, int64_t end_y, int64_t color_id) {
    DrawLine((int) start_x, (int) start_y, (int) end_x, (int) end_y, tb_raylib_color_from_id(color_id));
}

bool __tb_foreign_raylib_IsKeyDown(int64_t key) {
    return IsKeyDown((int) key);
}

void __tb_foreign_raylib_SetExitKey(int64_t key) {
    SetExitKey((int) key);
}

bool __tb_foreign_raylib_IsKeyPressed(int64_t key) {
    return IsKeyPressed((int) key);
}

int64_t __tb_foreign_raylib_GetCharPressed(void) {
    return GetCharPressed();
}

int64_t __tb_foreign_raylib_GetMouseX(void) {
    return GetMouseX();
}

int64_t __tb_foreign_raylib_GetMouseY(void) {
    return GetMouseY();
}

bool __tb_foreign_raylib_IsMouseButtonDown(int64_t button) {
    return IsMouseButtonDown((int) button);
}

void __tb_foreign_raylib_InitAudioDevice(void) {
    InitAudioDevice();
}

void __tb_foreign_raylib_CloseAudioDevice(void) {
    CloseAudioDevice();
}

int64_t __tb_foreign_raylib_LoadSound(const char *path) {
    Sound sound = LoadSound(path);
    if (sound.frameCount == 0) {
        return 0;
    }
    return tb_raylib_store_sound(sound);
}

void __tb_foreign_raylib_PlaySound(int64_t sound_handle) {
    Sound *sound = tb_raylib_sound_from_handle(sound_handle);
    if (sound == NULL) {
        return;
    }
    PlaySound(*sound);
}

void __tb_foreign_raylib_SetSoundVolume(int64_t sound_handle, int64_t volume_percent) {
    Sound *sound = tb_raylib_sound_from_handle(sound_handle);
    if (sound == NULL) {
        return;
    }
    if (volume_percent < 0) {
        volume_percent = 0;
    }
    if (volume_percent > 100) {
        volume_percent = 100;
    }
    SetSoundVolume(*sound, (float) volume_percent / 100.0f);
}

void __tb_foreign_raylib_UnloadSound(int64_t sound_handle) {
    Sound *sound = tb_raylib_sound_from_handle(sound_handle);
    if (sound == NULL) {
        return;
    }
    int64_t index = sound_handle - 1;
    UnloadSound(*sound);
    tb_raylib_sound_used[index] = false;
    tb_raylib_sounds[index] = (Sound) {0};
}

int64_t __tb_foreign_raylib_GetScreenWidth(void) {
    return GetScreenWidth();
}

int64_t __tb_foreign_raylib_GetScreenHeight(void) {
    return GetScreenHeight();
}

void __tb_foreign_raylib_CloseWindow(void) {
    CloseWindow();
}
