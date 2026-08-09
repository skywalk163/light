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

@.printf_fmt = private unnamed_addr constant [4 x i8] c"%d\0A\00"

define i32 @_主段(i32 %主段_args) {
  %1 = alloca i32, align 4
  %2 = fadd double 0.0, 3.14159
  store i32 %2, i32* %1, align 4
  %3 = alloca i32, align 4
  %4 = fadd double 0.0, 2.0
  store i32 %4, i32* %3, align 4
  %5 = alloca i32, align 4
  %6 = load i32, i32* %1, align 4
  %7 = load i32, i32* %3, align 4
  %8 = mul i32 %6, %7
  %9 = load i32, i32* %3, align 4
  %10 = mul i32 %8, %9
  store i32 %10, i32* %5, align 4
  %11 = load i32, i32* %5, align 4
  %12 = getelementptr inbounds [4 x i8], [4 x i8]* @.printf_fmt, i32 0, i32 0
  %13 = call i32 (i8*, ...) @printf(i8* %12, i32 %11)
  ret i32 0
}
