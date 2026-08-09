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
  %2 = add i64 0, 5
  %3 = call i32* @light_list_new(i64 %2)
  %4 = add i32 0, 10
  %5 = add i64 0, 0
  call void @light_list_set(i32* %3, i64 %5, i32 %4)
  %6 = add i32 0, 20
  %7 = add i64 0, 1
  call void @light_list_set(i32* %3, i64 %7, i32 %6)
  %8 = add i32 0, 30
  %9 = add i64 0, 2
  call void @light_list_set(i32* %3, i64 %9, i32 %8)
  %10 = add i32 0, 40
  %11 = add i64 0, 3
  call void @light_list_set(i32* %3, i64 %11, i32 %10)
  %12 = add i32 0, 50
  %13 = add i64 0, 4
  call void @light_list_set(i32* %3, i64 %13, i32 %12)
  store i32 %3, i32* %1, align 4
  %14 = alloca i32, align 4
  %15 = add i32 0, 0
  store i32 %15, i32* %14, align 4
  %16 = alloca i32, align 4
  %17 = add i32 0, 0
  store i32 %17, i32* %16, align 4
  %18 = alloca i32, align 4
  %19 = add i32 0, 0
  store i32 %19, i32* %18, align 4
  %20 = load i32, i32* %14, align 4
  %21 = getelementptr inbounds [4 x i8], [4 x i8]* @.printf_fmt, i32 0, i32 0
  %22 = call i32 (i8*, ...) @printf(i8* %21, i32 %20)
  %23 = load i32, i32* %16, align 4
  %24 = getelementptr inbounds [4 x i8], [4 x i8]* @.printf_fmt, i32 0, i32 0
  %25 = call i32 (i8*, ...) @printf(i8* %24, i32 %23)
  %26 = load i32, i32* %18, align 4
  %27 = getelementptr inbounds [4 x i8], [4 x i8]* @.printf_fmt, i32 0, i32 0
  %28 = call i32 (i8*, ...) @printf(i8* %27, i32 %26)
  ret i32 0
}
