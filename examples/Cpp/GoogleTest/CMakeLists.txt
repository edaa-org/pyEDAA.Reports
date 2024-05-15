cmake_minimum_required(VERSION 3.20)

# Project configuration
set(PROJECT_NAME Unittesting)
project(${PROJECT_NAME})
# * PROJECT_SOURCE_DIR - Top level source directory for the project
# * PROJECT_BINARY_DIR - Full path to build directory for project

# Compiler flags
set(CMAKE_CXX_FLAGS "-g -Wall")
set(CMAKE_CXX_STANDARD 20)

include_directories(${PROJECT_SOURCE_DIR}/src)
file(GLOB SRC_FILES ${PROJECT_SOURCE_DIR}/src/*.cpp)

# GoogleTest
add_subdirectory(./lib/googletest)
enable_testing()
#
# Include the gtest library. gtest_SOURCE_DIR is available due to
# 'project(gtest)' above.
include_directories(${gtest_SOURCE_DIR}/include ${gtest_SOURCE_DIR})

########################################
# Test files
########################################
file(GLOB TEST_SRC_FILES ${PROJECT_SOURCE_DIR}/test/*.cpp)

########################################
# Unit Tests
########################################
add_executable(runUnitTests ${TEST_SRC_FILES})
