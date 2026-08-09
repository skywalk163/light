; ModuleID = 'test_class_compile.ll'
source_filename = "test_class_compile.ll"
target datalayout = "e-m:w-p270:32:32-p271:32:32-p272:64:64-i64:64-i128:128-f80:128-n8:16:32:64-S128"
target triple = "x86_64-pc-windows-msvc19.37.32822"

@.printf_fmt = private unnamed_addr constant [4 x i8] c"%d\0A\00"
@.str.0 = private unnamed_addr constant [7 x i8] c"\E4\BD\A0\E5\A5\BD\00"

declare i32 @printf(ptr, ...)

declare i32 @puts(ptr)

declare i32 @fputs(ptr, ptr)

declare ptr @malloc(i64)

declare void @free(ptr)

declare double @sin(double)

declare double @cos(double)

declare double @tan(double)

declare double @exp(double)

declare double @log(double)

declare double @log10(double)

declare double @sqrt(double)

declare double @pow(double, double)

declare double @fabs(double)

declare double @floor(double)

declare double @ceil(double)

declare double @round(double)

declare double @cbrt(double)

declare double @fmod(double, double)

declare double @fmin(double, double)

declare double @fmax(double, double)

declare i32 @strlen(ptr)

declare ptr @strcpy(ptr, ptr)

declare ptr @strcat(ptr, ptr)

declare i32 @strcmp(ptr, ptr)

declare ptr @strstr(ptr, ptr)

declare ptr @fopen(ptr, ptr)

declare i32 @fclose(ptr)

declare i64 @fread(ptr, i64, i64, ptr)

declare i32 @fwrite(ptr, i64, i64, ptr)

declare ptr @light_list_new(i64)

declare i32 @light_list_length(ptr)

declare i32 @light_list_append(ptr, i32)

declare i32 @light_list_get(ptr, i64)

declare void @light_list_set(ptr, i64, i32)

declare ptr @light_list_copy(ptr)

declare void @light_list_free(ptr)

declare ptr @light_itoa(i32)

declare ptr @light_dict_new()

declare void @light_dict_set(ptr, ptr, i32)

declare i32 @light_dict_get(ptr, ptr)

declare i1 @light_dict_contains(ptr, ptr)

declare void @light_dict_remove(ptr, ptr)

declare void @light_dict_free(ptr)

define ptr @seg_1_465afe_ctor(i32 %args) {
  %1 = add i64 0, 1024
  %2 = call ptr @malloc(i64 %1)
  ret ptr %2
}

define i32 @seg_2_83fab3(ptr %this, i32 %args) {
  %1 = getelementptr inbounds [3 x i8], ptr @.str.0, i32 0, i32 0
  %2 = call i32 @puts(ptr %1)
  ret i32 0
}

define i32 @main() {
  %1 = alloca ptr, align 8
  %2 = call ptr @seg_1_465afe_ctor(i32 0)
  store ptr %2, ptr %1, align 8
  %3 = load ptr, ptr %1, align 8
  %4 = call i32 @seg_2_83fab3(ptr %3, i32 0)
  ret i32 0
}
