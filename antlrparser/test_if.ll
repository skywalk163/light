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
  %2 = add i32 0, 10
  store i32 %2, i32* %1, align 4
  %3 = load i32, i32* %1, align 4
  %4 = add i32 0, 5
  %6 = icmp sgt i32 %3, %4
  %7 = zext i1 %6 to i32
  %8 = icmp ne i32 %7, 0
  br i1 %8, label %if.then1, label %if.else2
  if.then1:
  %9 = add i32 0, 1
  %10 = getelementptr inbounds [4 x i8], [4 x i8]* @.printf_fmt, i32 0, i32 0
  %11 = call i32 (i8*, ...) @printf(i8* %10, i32 %9)
  br label %if.end3
if.else2:
  %12 = add i32 0, 0
  %13 = getelementptr inbounds [4 x i8], [4 x i8]* @.printf_fmt, i32 0, i32 0
  %14 = call i32 (i8*, ...) @printf(i8* %13, i32 %12)
  br label %if.end3
if.end3:
ret i32 0
}
