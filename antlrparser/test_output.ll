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
@.str.0 = private unnamed_addr constant [27 x i8] c"=== \E6\95\B0\E5\AD\A6\E5\87\BD\E6\95\B0\E6\B5\8B\E8\AF\95 ===\00"
@.str.1 = private unnamed_addr constant [11 x i8] c"sqrt(16): \00"
@.str.2 = private unnamed_addr constant [12 x i8] c"pow(2,10): \00"
@.str.3 = private unnamed_addr constant [11 x i8] c"abs(-42): \00"
@.str.4 = private unnamed_addr constant [1 x i8] c"\00"
@.str.5 = private unnamed_addr constant [27 x i8] c"=== \E5\88\97\E8\A1\A8\E6\93\8D\E4\BD\9C\E6\B5\8B\E8\AF\95 ===\00"
@.str.6 = private unnamed_addr constant [15 x i8] c"\E5\88\97\E8\A1\A8\E9\95\BF\E5\BA\A6: \00"
@.str.7 = private unnamed_addr constant [18 x i8] c"\E7\AC\AC\E4\B8\80\E4\B8\AA\E5\85\83\E7\B4\A0: \00"
@.str.8 = private unnamed_addr constant [15 x i8] c"\E5\85\83\E7\B4\A0\E6\80\BB\E5\92\8C: \00"
@.str.9 = private unnamed_addr constant [21 x i8] c"=== \E6\B5\8B\E8\AF\95\E5\AE\8C\E6\88\90 ===\00"

define i32 @main(i32 %main_args) {
  %1 = getelementptr inbounds [15 x i8], [15 x i8]* @.str.0, i32 0, i32 0
  %2 = call i32 @puts(i8* %1)
  %3 = alloca i32, align 4
  %4 = add i32 0, 16
  %5 = sitofp i32 %4 to double
  %6 = call double @sqrt(double %5)
  %7 = fptosi double %6 to i32
  store i32 %7, i32* %3, align 4
  %8 = getelementptr inbounds [11 x i8], [11 x i8]* @.str.1, i32 0, i32 0
  %9 = call i32 @puts(i8* %8)
  %10 = load i32, i32* %3, align 4
  %11 = getelementptr inbounds [4 x i8], [4 x i8]* @.printf_fmt, i32 0, i32 0
  %12 = call i32 (i8*, ...) @printf(i8* %11, i32 %10)
  %13 = alloca i32, align 4
  %14 = add i32 0, 2
  %15 = sitofp i32 %14 to double
  %16 = add i32 0, 10
  %17 = sitofp i32 %16 to double
  %18 = call double @pow(double %15, double %17)
  %19 = fptosi double %18 to i32
  store i32 %19, i32* %13, align 4
  %20 = getelementptr inbounds [12 x i8], [12 x i8]* @.str.2, i32 0, i32 0
  %21 = call i32 @puts(i8* %20)
  %22 = load i32, i32* %13, align 4
  %23 = getelementptr inbounds [4 x i8], [4 x i8]* @.printf_fmt, i32 0, i32 0
  %24 = call i32 (i8*, ...) @printf(i8* %23, i32 %22)
  %25 = alloca i32, align 4
  %26 = add i32 0, 0
  %27 = add i32 0, 42
  %28 = sub i32 %26, %27
  store i32 %28, i32* %25, align 4
  %29 = alloca i32, align 4
  %30 = load i32, i32* %25, align 4
  %31 = icmp slt i32 %30, 0
  %32 = sub i32 0, %30
  %33 = select i1 %31, i32 %32, i32 %30
  store i32 %33, i32* %29, align 4
  %34 = getelementptr inbounds [11 x i8], [11 x i8]* @.str.3, i32 0, i32 0
  %35 = call i32 @puts(i8* %34)
  %36 = load i32, i32* %29, align 4
  %37 = getelementptr inbounds [4 x i8], [4 x i8]* @.printf_fmt, i32 0, i32 0
  %38 = call i32 (i8*, ...) @printf(i8* %37, i32 %36)
  %39 = getelementptr inbounds [1 x i8], [1 x i8]* @.str.4, i32 0, i32 0
  %40 = call i32 @puts(i8* %39)
  %41 = getelementptr inbounds [15 x i8], [15 x i8]* @.str.5, i32 0, i32 0
  %42 = call i32 @puts(i8* %41)
  %43 = alloca i8*, align 8
  %44 = add i64 0, 5
  %45 = call i8* @light_list_new(i64 %44)
  %46 = bitcast i8* %45 to i32*
  %47 = add i32 0, 10
  %48 = add i64 0, 0
  call void @light_list_set(i32* %46, i64 %48, i32 %47)
  %49 = add i32 0, 20
  %50 = add i64 0, 1
  call void @light_list_set(i32* %46, i64 %50, i32 %49)
  %51 = add i32 0, 30
  %52 = add i64 0, 2
  call void @light_list_set(i32* %46, i64 %52, i32 %51)
  %53 = add i32 0, 40
  %54 = add i64 0, 3
  call void @light_list_set(i32* %46, i64 %54, i32 %53)
  %55 = add i32 0, 50
  %56 = add i64 0, 4
  call void @light_list_set(i32* %46, i64 %56, i32 %55)
  store i8* %45, i8** %43, align 8
  %57 = alloca i32, align 4
  %58 = load i8*, i8** %43, align 8
  %59 = bitcast i8* %58 to i32*
  %60 = call i32 @light_list_length(i32* %59)
  store i32 %60, i32* %57, align 4
  %61 = getelementptr inbounds [7 x i8], [7 x i8]* @.str.6, i32 0, i32 0
  %62 = call i32 @puts(i8* %61)
  %63 = load i32, i32* %57, align 4
  %64 = getelementptr inbounds [4 x i8], [4 x i8]* @.printf_fmt, i32 0, i32 0
  %65 = call i32 (i8*, ...) @printf(i8* %64, i32 %63)
  %66 = alloca i32, align 4
  %67 = load i8*, i8** %43, align 8
  %68 = add i32 0, 0
  %69 = zext i32 %68 to i64
  %70 = bitcast i8* %67 to i32*
  %71 = call i32 @light_list_get(i32* %70, i64 %69)
  store i32 %71, i32* %66, align 4
  %72 = getelementptr inbounds [8 x i8], [8 x i8]* @.str.7, i32 0, i32 0
  %73 = call i32 @puts(i8* %72)
  %74 = load i32, i32* %66, align 4
  %75 = getelementptr inbounds [4 x i8], [4 x i8]* @.printf_fmt, i32 0, i32 0
  %76 = call i32 (i8*, ...) @printf(i8* %75, i32 %74)
  %77 = alloca i32, align 4
  %78 = add i32 0, 0
  store i32 %78, i32* %77, align 4
  %79 = alloca i32, align 4
  %80 = add i32 0, 0
  store i32 %80, i32* %79, align 4
  br label %while.cond1
  while.cond1:
  %81 = load i32, i32* %79, align 4
  %82 = load i32, i32* %57, align 4
  %84 = icmp slt i32 %81, %82
  %85 = zext i1 %84 to i32
  %86 = icmp ne i32 %85, 0
  br i1 %86, label %while.body2, label %while.end3
  while.body2:
  %87 = load i32, i32* %77, align 4
  %88 = load i8*, i8** %43, align 8
  %89 = load i32, i32* %79, align 4
  %90 = zext i32 %89 to i64
  %91 = bitcast i8* %88 to i32*
  %92 = call i32 @light_list_get(i32* %91, i64 %90)
  %93 = add i32 %87, %92
  store i32 %93, i32* %77, align 4
  %94 = load i32, i32* %79, align 4
  %95 = add i32 0, 1
  %96 = add i32 %94, %95
  store i32 %96, i32* %79, align 4
  br label %while.cond1
while.end3:
%97 = getelementptr inbounds [7 x i8], [7 x i8]* @.str.8, i32 0, i32 0
%98 = call i32 @puts(i8* %97)
%99 = load i32, i32* %77, align 4
%100 = getelementptr inbounds [4 x i8], [4 x i8]* @.printf_fmt, i32 0, i32 0
%101 = call i32 (i8*, ...) @printf(i8* %100, i32 %99)
%102 = getelementptr inbounds [1 x i8], [1 x i8]* @.str.4, i32 0, i32 0
%103 = call i32 @puts(i8* %102)
%104 = getelementptr inbounds [13 x i8], [13 x i8]* @.str.9, i32 0, i32 0
%105 = call i32 @puts(i8* %104)
ret i32 0
}
