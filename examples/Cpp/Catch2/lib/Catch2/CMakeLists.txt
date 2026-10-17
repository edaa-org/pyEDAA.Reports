include(FetchContent)

FetchContent_Declare(
  Catch2
  GIT_REPOSITORY https://github.com/catchorg/Catch2.git
  GIT_TAG        317ac1ed4c0bb6e6b91eafc817e05c488feffcb3 # v3.16.0
)

FetchContent_MakeAvailable(Catch2)
