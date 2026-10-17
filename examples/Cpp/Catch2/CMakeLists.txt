cmake_minimum_required(VERSION 3.20)

# Project configuration
set(PROJECT_NAME Unittesting)
project(${PROJECT_NAME})
# * PROJECT_SOURCE_DIR - Top level source directory for the project
# * PROJECT_BINARY_DIR - Full path to build directory for project

# Compiler flags
set(CMAKE_CXX_FLAGS "-g -Wall")
set(CMAKE_CXX_STANDARD 20)

file(GLOB SRC_FILES ${PROJECT_SOURCE_DIR}/src/*.[ch]pp)

add_library(app STATIC ${SRC_FILES})
target_include_directories(app PUBLIC ${PROJECT_SOURCE_DIR}/src)

# Code coverage of the library (gcov)
target_compile_options(app PRIVATE --coverage)
target_link_options(app INTERFACE --coverage)

# Catch2
add_subdirectory(./lib/Catch2)

########################################
# Test files
########################################
file(GLOB TEST_SRC_FILES ${PROJECT_SOURCE_DIR}/test/*.[ch]pp)

########################################
# Unit Tests
########################################
add_executable(unit_tests ${TEST_SRC_FILES})
target_link_libraries(unit_tests app Catch2::Catch2WithMain)
