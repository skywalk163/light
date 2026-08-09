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

@.printf_fmt = private unnamed_addr constant [4 x i8] c"%d\0A\00"
@.str.0 = private unnamed_addr constant [21 x i8] c"=== \E5\88\97\E8\A1\A8\E6\B5\8B\E8\AF\95 ===\00"
@.str.1 = private unnamed_addr constant [12 x i8] c"\E7\AC\AC\E4\B8\80\E4\B8\AA: \00"
@.str.2 = private unnamed_addr constant [12 x i8] c"\E7\AC\AC\E4\BA\8C\E4\B8\AA: \00"
@.str.3 = private unnamed_addr constant [15 x i8] c"\E6\9C\80\E5\90\8E\E4\B8\80\E4\B8\AA: \00"
@.str.4 = private unnamed_addr constant [9 x i8] c"\E6\80\BB\E5\92\8C: \00"
@.str.5 = private unnamed_addr constant [1 x i8] c"\00"
@.str.6 = private unnamed_addr constant [21 x i8] c"=== \E6\B5\8B\E8\AF\95\E5\AE\8C\E6\88\90 ===\00"

define i32 @main(i32 %main_args) {
  %1 = getelementptr inbounds [13 x i8], [13 x i8]* @.str.0, i32 0, i32 0
  %2 = call i32 @puts(i8* %1)
  %3 = alloca i8*, align 8
  %4 = add i64 0, 5
  %5 = call i8* @light_list_new(i64 %4)
  %6 = bitcast i8* %5 to i32*
  %7 = add i32 0, 10
  %8 = add i64 0, 0
  call void @light_list_set(i32* %6, i64 %8, i32 %7)
  %9 = add i32 0, 20
  %10 = add i64 0, 1
  call void @light_list_set(i32* %6, i64 %10, i32 %9)
  %11 = add i32 0, 30
  %12 = add i64 0, 2
  call void @light_list_set(i32* %6, i64 %12, i32 %11)
  %13 = add i32 0, 40
  %14 = add i64 0, 3
  call void @light_list_set(i32* %6, i64 %14, i32 %13)
  %15 = add i32 0, 50
  %16 = add i64 0, 4
  call void @light_list_set(i32* %6, i64 %16, i32 %15)
  store i8* %5, i8** %3, align 8
  %17 = alloca i32, align 4
  %18 = load i8*, i8** %3, align 8
  %19 = add i32 0, 0
  %20 = zext i32 %19 to i64
  %21 = bitcast i8* %18 to i32*
  %22 = call i32 @light_list_get(i32* %21, i64 %20)
  store i32 %22, i32* %17, align 4
  %23 = alloca i32, align 4
  %24 = load i8*, i8** %3, align 8
  %25 = add i32 0, 1
  %26 = zext i32 %25 to i64
  %27 = bitcast i8* %24 to i32*
  %28 = call i32 @light_list_get(i32* %27, i64 %26)
  store i32 %28, i32* %23, align 4
  %29 = alloca i32, align 4
  %30 = load i8*, i8** %3, align 8
  %31 = add i32 0, 4
  %32 = zext i32 %31 to i64
  %33 = bitcast i8* %30 to i32*
  %34 = call i32 @light_list_get(i32* %33, i64 %32)
  store i32 %34, i32* %29, align 4
  %35 = getelementptr inbounds [6 x i8], [6 x i8]* @.str.1, i32 0, i32 0
  %36 = call i32 @puts(i8* %35)
  %37 = load i32, i32* %17, align 4
  %38 = getelementptr inbounds [4 x i8], [4 x i8]* @.printf_fmt, i32 0, i32 0
  %39 = call i32 (i8*, ...) @printf(i8* %38, i32 %37)
  %40 = getelementptr inbounds [6 x i8], [6 x i8]* @.str.2, i32 0, i32 0
  %41 = call i32 @puts(i8* %40)
  %42 = load i32, i32* %23, align 4
  %43 = getelementptr inbounds [4 x i8], [4 x i8]* @.printf_fmt, i32 0, i32 0
  %44 = call i32 (i8*, ...) @printf(i8* %43, i32 %42)
  %45 = getelementptr inbounds [7 x i8], [7 x i8]* @.str.3, i32 0, i32 0
  %46 = call i32 @puts(i8* %45)
  %47 = load i32, i32* %29, align 4
  %48 = getelementptr inbounds [4 x i8], [4 x i8]* @.printf_fmt, i32 0, i32 0
  %49 = call i32 (i8*, ...) @printf(i8* %48, i32 %47)
  %50 = alloca i32, align 4
  %51 = load i32, i32* %17, align 4
  %52 = load i32, i32* %23, align 4
  %53 = add i32 %51, %52
  %54 = load i32, i32* %29, align 4
  %55 = add i32 %53, %54
  store i32 %55, i32* %50, align 4
  %56 = getelementptr inbounds [5 x i8], [5 x i8]* @.str.4, i32 0, i32 0
  %57 = call i32 @puts(i8* %56)
  %58 = load i32, i32* %50, align 4
  %59 = getelementptr inbounds [4 x i8], [4 x i8]* @.printf_fmt, i32 0, i32 0
  %60 = call i32 (i8*, ...) @printf(i8* %59, i32 %58)
  %61 = getelementptr inbounds [1 x i8], [1 x i8]* @.str.5, i32 0, i32 0
  %62 = call i32 @puts(i8* %61)
  %63 = getelementptr inbounds [13 x i8], [13 x i8]* @.str.6, i32 0, i32 0
  %64 = call i32 @puts(i8* %63)
  ret i32 0
}
