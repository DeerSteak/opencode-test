cmake_minimum_required(VERSION 3.16)
project(reverse LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

if(APPLE)
  list(APPEND CMAKE_PREFIX_PATH
       "/opt/homebrew/opt/qt"
       "/opt/homebrew/opt/qt@5"
       "/usr/local/opt/qt")
endif()

find_package(Qt6 COMPONENTS Widgets QUIET)
if(Qt6_FOUND)
  set(QT_LIB Qt6::Widgets)
else()
  find_package(Qt5 COMPONENTS Widgets REQUIRED)
  set(QT_LIB Qt5::Widgets)
endif()

add_executable(reverse main.cpp)
target_link_libraries(reverse PRIVATE ${QT_LIB})
