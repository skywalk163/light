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
declare i8* @light_dict_new()
declare void @light_dict_set(i8*, i8*, i32)
declare i32 @light_dict_get(i8*, i8*)
declare i1 @light_dict_contains(i8*, i8*)
declare void @light_dict_remove(i8*, i8*)
declare void @light_dict_free(i8*)

@.printf_fmt = private unnamed_addr constant [4 x i8] c"%d\0A\00"

define i32 @_主段(i32 %主段_args) {
  %1 = alloca i32, align 4
  %2 = call i32* @light_list_new(i64 0)
  store i32 %2, i32* %1, align 4
  %3 = add i32 0, 0
  %4 = add i32 0, 0
  %5 = add i32 0, 0
  %6 = alloca i32, align 4
  %7 = add i32 0, 0
  store i32 %7, i32* %6, align 4
  %8 = load i32, i32* %6, align 4
  %9 = getelementptr inbounds [4 x i8], [4 x i8]* @.printf_fmt, i32 0, i32 0
  %10 = call i32 (i8*, ...) @printf(i8* %9, i32 %8)
  %11 = alloca i32, align 4
  %12 = add i32 0, 0
  %13 = add i32 0, 0
  %14 = add i32 %12, %13
  %15 = add i32 0, 0
  %16 = add i32 %14, %15
  store i32 %16, i32* %11, align 4
  %17 = load i32, i32* %11, align 4
  %18 = getelementptr inbounds [4 x i8], [4 x i8]* @.printf_fmt, i32 0, i32 0
  %19 = call i32 (i8*, ...) @printf(i8* %18, i32 %17)
  ret i32 0
}
