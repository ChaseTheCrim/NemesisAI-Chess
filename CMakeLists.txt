cmake_minimum_required(VERSION 3.16)
project(ChessBotUI VERSION 1.0 LANGUAGES CXX)

# VS Code IntelliSense motoru için
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# İşte sihirli satır: Qt'nin MinGW yolu
set(CMAKE_PREFIX_PATH "C:/Qt/6.10.1/mingw_64" CACHE PATH "Qt Path")

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Qt'nin otomatik derleme araçlarını aktif ediyoruz
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

# Qt6 kütüphanelerini bul (Kendi sistemine göre path ayarı gerekebilir)
find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets)

# Kaynak dosyalarımız
add_executable(ChessBotUI
    main.cpp
    ChessBoard.cpp
    ChessBoard.h
    ChessPiece.cpp
    ChessPiece.h
)

# Qt kütüphanelerini projemize linkliyoruz
target_link_libraries(ChessBotUI PRIVATE Qt6::Core Qt6::Gui Qt6::Widgets)