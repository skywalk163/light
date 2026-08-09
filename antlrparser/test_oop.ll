; 光明 (Light) 编译输出
target triple = "x86_64-pc-windows-msvc"

declare i32 @printf(i8*, ...)
declare i32 @puts(i8*)
declare i32 @fputs(i8*, i8*)
declare i8* @malloc(i64)
declare void @free(i8*)
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
declare i32 @strlen(i8*)
declare i8* @strcpy(i8*, i8*)
declare i8* @strcat(i8*, i8*)
declare i32 @strcmp(i8*, i8*)
declare i8* @strstr(i8*, i8*)
declare i8* @fopen(i8*, i8*)
declare i32 @fclose(i8*)
declare i64 @fread(i8*, i64, i64, i8*)
declare i32 @fwrite(i8*, i64, i64, i8*)
declare i32* @light_list_new(i64)
declare i32 @light_list_length(i32*)
declare i32 @light_list_append(i32*, i32)
declare i32 @light_list_get(i32*, i64)
declare void @light_list_set(i32*, i64, i32)
declare i32* @light_list_copy(i32*)
declare void @light_list_free(i32*)
declare i8* @light_itoa(i32)
declare i8* @light_dict_new()
declare void @light_dict_set(i8*, i8*, i32)
declare i32 @light_dict_get(i8*, i8*)
declare i1 @light_dict_contains(i8*, i8*)
declare void @light_dict_remove(i8*, i8*)
declare void @light_dict_free(i8*)

; 类 人 的方法 说话
@.printf_fmt = private unnamed_addr constant [4 x i8] c"%d\0A\00"
@.str.0 = private unnamed_addr constant [7 x i8] c"\E4\BD\A0\E5\A5\BD\00"

define i32 @seg_1_说话(i8* %this, i32 %args) {
  %1 = getelementptr inbounds [3 x i8], [3 x i8]* @.str.0, i32 0, i32 0
  %2 = call i32 @puts(i8* %1)
  ret i32 0
}

define i32 @main() {
  %1 = alloca i8*, align 8
  %2 = call i8* @seg_1_ctor(i32 0)
  store i8* %2, i8** %1, align 8
  %3 = load i8*, i8** %1, align 8
  %4 = call i32 @seg_1_说话(i8* %3, i32 0)
  ret i32 0
}
