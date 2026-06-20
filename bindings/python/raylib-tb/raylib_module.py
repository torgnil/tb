# Copyright 2026 Torbjörn Nilsson
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import os
from pathlib import Path

from compiler_py.foreign_modules import ForeignConstant, ForeignFunction, ForeignModule


RAYLIB_DEFAULT_ROOT = Path("/opt/homebrew/Cellar/raylib/5.5")
RAYLIB_ROOT = Path(os.environ.get("TB_RAYLIB_ROOT", str(RAYLIB_DEFAULT_ROOT)))
RAYLIB_INCLUDE = Path(os.environ.get("TB_RAYLIB_INCLUDE", str(RAYLIB_ROOT / "include")))
RAYLIB_LIB = Path(os.environ.get("TB_RAYLIB_LIB", str(RAYLIB_ROOT / "lib")))
RAYLIB_DYLIB = RAYLIB_LIB / "libraylib.550.dylib"
RAYLIB_WRAPPER_C = Path(__file__).resolve().parent / "raylib_tb.c"


FOREIGN_MODULE = ForeignModule(
    name="raylib",
    functions=(
        ForeignFunction("InitWindow", "__tb_foreign_raylib_InitWindow", ("int", "int", "string"), "void", "declare void @__tb_foreign_raylib_InitWindow(i64, i64, ptr)"),
        ForeignFunction("WindowShouldClose", "__tb_foreign_raylib_WindowShouldClose", (), "bool", "declare i1 @__tb_foreign_raylib_WindowShouldClose()"),
        ForeignFunction("GetFrameTimeMillis", "__tb_foreign_raylib_GetFrameTimeMillis", (), "int", "declare i64 @__tb_foreign_raylib_GetFrameTimeMillis()"),
        ForeignFunction("GetTimeMillis", "__tb_foreign_raylib_GetTimeMillis", (), "int", "declare i64 @__tb_foreign_raylib_GetTimeMillis()"),
        ForeignFunction("SetTargetFPS", "__tb_foreign_raylib_SetTargetFPS", ("int",), "void", "declare void @__tb_foreign_raylib_SetTargetFPS(i64)"),
        ForeignFunction("BeginDrawing", "__tb_foreign_raylib_BeginDrawing", (), "void", "declare void @__tb_foreign_raylib_BeginDrawing()"),
        ForeignFunction("EndDrawing", "__tb_foreign_raylib_EndDrawing", (), "void", "declare void @__tb_foreign_raylib_EndDrawing()"),
        ForeignFunction("ClearBackground", "__tb_foreign_raylib_ClearBackground", ("int",), "void", "declare void @__tb_foreign_raylib_ClearBackground(i64)"),
        ForeignFunction("LoadTexture", "__tb_foreign_raylib_LoadTexture", ("string",), "int", "declare i64 @__tb_foreign_raylib_LoadTexture(ptr)"),
        ForeignFunction("DrawText", "__tb_foreign_raylib_DrawText", ("string", "int", "int", "int", "int"), "void", "declare void @__tb_foreign_raylib_DrawText(ptr, i64, i64, i64, i64)"),
        ForeignFunction("DrawTexture", "__tb_foreign_raylib_DrawTexture", ("int", "int", "int", "int"), "void", "declare void @__tb_foreign_raylib_DrawTexture(i64, i64, i64, i64)"),
        ForeignFunction("UnloadTexture", "__tb_foreign_raylib_UnloadTexture", ("int",), "void", "declare void @__tb_foreign_raylib_UnloadTexture(i64)"),
        ForeignFunction("DrawRectangle", "__tb_foreign_raylib_DrawRectangle", ("int", "int", "int", "int", "int"), "void", "declare void @__tb_foreign_raylib_DrawRectangle(i64, i64, i64, i64, i64)"),
        ForeignFunction("DrawCircle", "__tb_foreign_raylib_DrawCircle", ("int", "int", "int", "int"), "void", "declare void @__tb_foreign_raylib_DrawCircle(i64, i64, i64, i64)"),
        ForeignFunction("DrawLine", "__tb_foreign_raylib_DrawLine", ("int", "int", "int", "int", "int"), "void", "declare void @__tb_foreign_raylib_DrawLine(i64, i64, i64, i64, i64)"),
        ForeignFunction("IsKeyDown", "__tb_foreign_raylib_IsKeyDown", ("int",), "bool", "declare i1 @__tb_foreign_raylib_IsKeyDown(i64)"),
        ForeignFunction("IsKeyPressed", "__tb_foreign_raylib_IsKeyPressed", ("int",), "bool", "declare i1 @__tb_foreign_raylib_IsKeyPressed(i64)"),
        ForeignFunction("GetMouseX", "__tb_foreign_raylib_GetMouseX", (), "int", "declare i64 @__tb_foreign_raylib_GetMouseX()"),
        ForeignFunction("GetMouseY", "__tb_foreign_raylib_GetMouseY", (), "int", "declare i64 @__tb_foreign_raylib_GetMouseY()"),
        ForeignFunction("IsMouseButtonDown", "__tb_foreign_raylib_IsMouseButtonDown", ("int",), "bool", "declare i1 @__tb_foreign_raylib_IsMouseButtonDown(i64)"),
        ForeignFunction("InitAudioDevice", "__tb_foreign_raylib_InitAudioDevice", (), "void", "declare void @__tb_foreign_raylib_InitAudioDevice()"),
        ForeignFunction("CloseAudioDevice", "__tb_foreign_raylib_CloseAudioDevice", (), "void", "declare void @__tb_foreign_raylib_CloseAudioDevice()"),
        ForeignFunction("LoadSound", "__tb_foreign_raylib_LoadSound", ("string",), "int", "declare i64 @__tb_foreign_raylib_LoadSound(ptr)"),
        ForeignFunction("PlaySound", "__tb_foreign_raylib_PlaySound", ("int",), "void", "declare void @__tb_foreign_raylib_PlaySound(i64)"),
        ForeignFunction("SetSoundVolume", "__tb_foreign_raylib_SetSoundVolume", ("int", "int"), "void", "declare void @__tb_foreign_raylib_SetSoundVolume(i64, i64)"),
        ForeignFunction("UnloadSound", "__tb_foreign_raylib_UnloadSound", ("int",), "void", "declare void @__tb_foreign_raylib_UnloadSound(i64)"),
        ForeignFunction("GetScreenWidth", "__tb_foreign_raylib_GetScreenWidth", (), "int", "declare i64 @__tb_foreign_raylib_GetScreenWidth()"),
        ForeignFunction("GetScreenHeight", "__tb_foreign_raylib_GetScreenHeight", (), "int", "declare i64 @__tb_foreign_raylib_GetScreenHeight()"),
        ForeignFunction("CloseWindow", "__tb_foreign_raylib_CloseWindow", (), "void", "declare void @__tb_foreign_raylib_CloseWindow()"),
    ),
    constants=(
        ForeignConstant("BLACK", "__tb_foreign_raylib_BLACK", "int", "0"),
        ForeignConstant("WHITE", "__tb_foreign_raylib_WHITE", "int", "1"),
        ForeignConstant("RED", "__tb_foreign_raylib_RED", "int", "2"),
        ForeignConstant("GREEN", "__tb_foreign_raylib_GREEN", "int", "3"),
        ForeignConstant("BLUE", "__tb_foreign_raylib_BLUE", "int", "4"),
        ForeignConstant("YELLOW", "__tb_foreign_raylib_YELLOW", "int", "5"),
        ForeignConstant("RAYWHITE", "__tb_foreign_raylib_RAYWHITE", "int", "6"),
        ForeignConstant("LIGHTGRAY", "__tb_foreign_raylib_LIGHTGRAY", "int", "7"),
        ForeignConstant("DARKGRAY", "__tb_foreign_raylib_DARKGRAY", "int", "8"),
        ForeignConstant("KEY_SPACE", "__tb_foreign_raylib_KEY_SPACE", "int", "32"),
        ForeignConstant("KEY_ESCAPE", "__tb_foreign_raylib_KEY_ESCAPE", "int", "256"),
        ForeignConstant("KEY_RIGHT", "__tb_foreign_raylib_KEY_RIGHT", "int", "262"),
        ForeignConstant("KEY_LEFT", "__tb_foreign_raylib_KEY_LEFT", "int", "263"),
        ForeignConstant("KEY_DOWN", "__tb_foreign_raylib_KEY_DOWN", "int", "264"),
        ForeignConstant("KEY_UP", "__tb_foreign_raylib_KEY_UP", "int", "265"),
        ForeignConstant("MOUSE_BUTTON_LEFT", "__tb_foreign_raylib_MOUSE_BUTTON_LEFT", "int", "0"),
        ForeignConstant("MOUSE_BUTTON_RIGHT", "__tb_foreign_raylib_MOUSE_BUTTON_RIGHT", "int", "1"),
        ForeignConstant("MOUSE_BUTTON_MIDDLE", "__tb_foreign_raylib_MOUSE_BUTTON_MIDDLE", "int", "2"),
    ),
    link_flags=(str(RAYLIB_DYLIB), f"-Wl,-rpath,{RAYLIB_LIB}"),
    cflags=(f"-I{RAYLIB_INCLUDE}",),
    c_sources=(str(RAYLIB_WRAPPER_C),),
)

RAYLIB_MODULE = FOREIGN_MODULE
