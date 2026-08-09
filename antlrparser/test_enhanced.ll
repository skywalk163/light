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
@.str.0 = private unnamed_addr constant [11 x i8] c"Hello LLVM\00"

define i32 @main() {
  %1 = alloca i32, align 4
  %2 = alloca i32, align 4
  %3 = alloca i32, align 4
  %4 = alloca i32, align 4
  %5 = fadd double 0.0, 3.14159
  store i32 %5, i32* %1, align 4
  %6 = add i32 0, 10
  store i32 %6, i32* %2, align 4
  %7 = load i32, i32* %1, align 4
  %8 = load i32, i32* %2, align 4
  %9 = mul i32 %7, %8
  %10 = load i32, i32* %2, align 4
  %11 = mul i32 %9, %10
  store i32 %11, i32* %3, align 4
  %12 = load i32, i32* %3, align 4
  %13 = getelementptr inbounds [4 x i8], [4 x i8]* @.printf_fmt, i32 0, i32 0
  %14 = call i32 (i8*, ...) @printf(i8* %13, i32 %12)
  %15 = getelementptr inbounds [11 x i8], [11 x i8]* @.str.0, i32 0, i32 0
  store i32 %15, i32* %4, align 4
  %16 = load i32, i32* %4, align 4
  %17 = call i32 @strlen(i8* %16)
  %18 = getelementptr inbounds [4 x i8], [4 x i8]* @.printf_fmt, i32 0, i32 0
  %19 = call i32 (i8*, ...) @printf(i8* %18, i32 %17)
  ret i32 0
}
