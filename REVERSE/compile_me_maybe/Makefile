CXX ?= c++
CXXFLAGS ?= -std=c++17 -O2 -Wall -Wextra -pedantic -Iinclude

BUILD_DIR := build
TARGET := $(BUILD_DIR)/compile_me_maybe

.PHONY: all run clean

all: $(TARGET)

$(TARGET): src/main.cpp include/vm.hpp include/data.hpp include/generated_witness.hpp | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) src/main.cpp -o $@

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

run: $(TARGET)
	./$(TARGET)

clean:
	rm -rf $(BUILD_DIR)
