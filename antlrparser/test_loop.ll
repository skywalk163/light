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
  %2 = add i32 0, 0
  store i32 %2, i32* %1, align 4
  %3 = alloca i32, align 4
  %4 = add i32 0, 0
  store i32 %4, i32* %3, align 4
  br label %while.cond1
  while.cond1:
  %5 = load i32, i32* %3, align 4
  %6 = add i32 0, 100
  %8 = icmp slt i32 %5, %6
  %9 = zext i1 %8 to i32
  %10 = icmp ne i32 %9, 0
  br i1 %10, label %while.body2, label %while.end3
  while.body2:
  %11 = load i32, i32* %1, align 4
  %12 = load i32, i32* %3, align 4
  %13 = add i32 %11, %12
  store i32 %13, i32* %1, align 4
  %14 = load i32, i32* %3, align 4
  %15 = add i32 0, 1
  %16 = add i32 %14, %15
  store i32 %16, i32* %3, align 4
  br label %while.cond1
while.end3:
%17 = load i32, i32* %1, align 4
%18 = getelementptr inbounds [4 x i8], [4 x i8]* @.printf_fmt, i32 0, i32 0
%19 = call i32 (i8*, ...) @printf(i8* %18, i32 %17)
ret i32 0
}
