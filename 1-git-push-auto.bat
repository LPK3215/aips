@echo off
setlocal enabledelayedexpansion
REM ===== 强制设置 UTF-8 编码 =====
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set LANG=zh_CN.UTF-8
cd /d "%~dp0"
title Git Push - 万能推送脚本

REM ========================================
REM   默认配置区（可根据需要修改）
REM ========================================
set DEFAULT_REPO=https://github.com/LPK3215/aips.git
set DEFAULT_EMAIL=17538703215@163.com
set DEFAULT_NAME=LPK3215
set DEFAULT_BRANCH=main
set DEFAULT_COMMIT_MSG=update
set PROXY_ADDR=127.0.0.1:7897
set GITHUB_NEW_REPO=https://github.com/new
set GITEE_NEW_REPO=https://gitee.com/projects/new
REM ========================================

echo ========================================
echo   Git 万能推送脚本
echo ========================================
echo.

REM ========================================
REM   显示当前绑定的远程仓库
REM ========================================
echo [仓库信息]
if exist ".git" (
    for /f "delims=" %%i in ('git remote get-url origin 2^>nul') do (
        echo   当前远程仓库: %%i
    )
    if errorlevel 1 echo   当前远程仓库: 未绑定
    for /f "delims=" %%i in ('git branch --show-current 2^>nul') do (
        echo   当前分支: %%i
    )
) else (
    echo   当前远程仓库: 未初始化Git
)
echo   默认远程仓库: %DEFAULT_REPO%
echo   默认分支: %DEFAULT_BRANCH% (GitHub新仓库默认为main)
echo ========================================
echo.

REM ========================================
REM   第一步：配置网络代理和Git设置
REM ========================================
echo [1/5] 配置网络代理...
git config --local http.proxy http://%PROXY_ADDR%
git config --local https.proxy http://%PROXY_ADDR%
git config --global core.quotepath false
echo 已设置代理: %PROXY_ADDR%
echo.

REM ========================================
REM   第二步：检查/初始化 Git 仓库
REM ========================================
echo [2/5] 检查Git仓库...
if not exist ".git" (
    echo [提示] 当前目录不是Git仓库
    set /p DO_INIT=是否要初始化为Git仓库？（输入 yes 或直接回车取消）: 
    if /i "!DO_INIT!"=="yes" (
        echo 正在初始化Git仓库...
        git init -b %DEFAULT_BRANCH%
        if errorlevel 1 (
            REM 旧版本 Git 不支持 -b 参数，使用传统方式
            git init
            git checkout -b %DEFAULT_BRANCH% 2>nul
        )
        echo 初始化完成
        echo.
    ) else (
        echo 已取消操作
        pause
        exit /b
    )
) else (
    echo Git仓库已存在
    echo.
)

REM ========================================
REM   第三步：配置远程仓库地址
REM ========================================
echo [3/5] 检查远程仓库...
set CURRENT_REPO=
for /f "delims=" %%i in ('git remote get-url origin 2^>nul') do set CURRENT_REPO=%%i
set FINAL_REPO=

if "!CURRENT_REPO!"=="" (
    echo [提示] 未检测到远程仓库地址
    echo.
    echo 如果还没有创建远程仓库，请先去创建：
    echo   [1] GitHub:  %GITHUB_NEW_REPO%
    echo   [2] Gitee:   %GITEE_NEW_REPO%
    echo.
    echo 创建完成后，复制仓库地址粘贴到下方
    echo 默认地址: %DEFAULT_REPO%
    echo.
    set /p INPUT_REPO=请输入远程仓库地址（直接回车使用默认）: 
    if "!INPUT_REPO!"=="" (
        set FINAL_REPO=%DEFAULT_REPO%
    ) else (
        set FINAL_REPO=!INPUT_REPO!
    )
    git remote add origin "!FINAL_REPO!" 2>nul
    if errorlevel 1 (
        echo [警告] 添加远程仓库失败，可能已存在，尝试更新...
        git remote set-url origin "!FINAL_REPO!"
    )
    echo 已设置远程仓库: !FINAL_REPO!
    echo.
) else (
    set FINAL_REPO=!CURRENT_REPO!
    echo [当前远程仓库] !CURRENT_REPO!
    set /p INPUT_REPO=直接回车使用当前地址，或输入新地址: 
    if not "!INPUT_REPO!"=="" (
        set FINAL_REPO=!INPUT_REPO!
        git remote set-url origin "!FINAL_REPO!"
        echo 已更新远程仓库: !FINAL_REPO!
    )
    echo.
)

REM ========================================
REM   第四步：检查用户身份配置
REM ========================================
echo [4/5] 检查用户身份...
set GIT_EMAIL=
set GIT_NAME=
for /f "delims=" %%i in ('git config --global user.email 2^>nul') do set GIT_EMAIL=%%i
for /f "delims=" %%i in ('git config --global user.name 2^>nul') do set GIT_NAME=%%i

if "!GIT_EMAIL!"=="" (
    echo [提示] 检测到未配置Git用户邮箱
    echo 默认邮箱: %DEFAULT_EMAIL%
    set /p INPUT_EMAIL=请输入邮箱（直接回车使用默认）: 
    if "!INPUT_EMAIL!"=="" (
        set GIT_EMAIL=%DEFAULT_EMAIL%
    ) else (
        set GIT_EMAIL=!INPUT_EMAIL!
    )
    git config --global user.email "!GIT_EMAIL!"
    echo 已设置邮箱: !GIT_EMAIL!
) else (
    echo 当前邮箱: !GIT_EMAIL!
)

if "!GIT_NAME!"=="" (
    echo [提示] 检测到未配置Git用户名
    echo 默认用户名: %DEFAULT_NAME%
    set /p INPUT_NAME=请输入用户名（直接回车使用默认）: 
    if "!INPUT_NAME!"=="" (
        set GIT_NAME=%DEFAULT_NAME%
    ) else (
        set GIT_NAME=!INPUT_NAME!
    )
    git config --global user.name "!GIT_NAME!"
    echo 已设置用户名: !GIT_NAME!
) else (
    echo 当前用户名: !GIT_NAME!
)
echo.

REM ========================================
REM   第五步：检查 .gitignore 变化并清理
REM ========================================
echo [5/6] 检查 .gitignore 变化...
echo.

REM 检查 .gitignore 是否有改动
git diff --cached --name-only | findstr /i "\.gitignore" >nul 2>&1
if not errorlevel 1 (
    echo [检测到] .gitignore 文件有改动
    echo.
    echo 是否要从远程仓库中删除新添加到 .gitignore 的文件？
    echo （这会删除远程仓库中的文件，但保留本地文件）
    echo.
    set /p CLEAN_IGNORED=输入 yes 清理远程仓库，直接回车跳过: 
    if /i "!CLEAN_IGNORED!"=="yes" (
        echo.
        echo 正在分析 .gitignore 中新增的规则...
        echo.
        
        REM 获取所有被 .gitignore 忽略但仍在 Git 追踪中的文件
        for /f "delims=" %%f in ('git ls-files -i --exclude-standard 2^>nul') do (
            echo   发现: %%f
            git rm -r --cached "%%f" >nul 2>&1
        )
        
        echo.
        echo [完成] 已从 Git 追踪中移除这些文件
        echo [提示] 本地文件仍然保留，只是不会再推送到远程
        echo.
    ) else (
        echo 已跳过清理步骤
        echo.
    )
) else (
    echo .gitignore 无改动，跳过清理检查
    echo.
)

REM ========================================
REM   第六步：添加、提交、推送
REM ========================================
echo [6/6] 准备推送...
echo.
echo ----------------------------------------
echo   当前改动的文件:
echo ----------------------------------------
git status --short
echo ----------------------------------------
echo.

set /p ADD_FILES=直接回车添加所有文件，或输入指定文件路径（多个用空格分开）: 
if "!ADD_FILES!"=="" (
    echo 正在添加所有文件...
    git add .
) else (
    echo 正在添加指定文件...
    git add !ADD_FILES!
)

REM 检查是否有需要提交的改动
git diff --cached --quiet
set HAS_STAGED_CHANGES=%errorlevel%

if %HAS_STAGED_CHANGES% equ 1 (
    echo.
    set /p COMMIT_MSG=请输入提交信息（直接回车默认为 "%DEFAULT_COMMIT_MSG%"）: 
    if "!COMMIT_MSG!"=="" set COMMIT_MSG=%DEFAULT_COMMIT_MSG%
    echo 正在提交...
    git commit -m "!COMMIT_MSG!"
    echo.
) else (
    echo.
    echo [提示] 暂存区没有改动，跳过提交步骤
    echo.
)

REM 检查是否有未推送的提交
set HAS_UNPUSHED=0
if %HAS_STAGED_CHANGES% equ 1 (
    set HAS_UNPUSHED=1
) else (
    REM 获取当前分支名
    set CHECK_BRANCH=
    for /f "delims=" %%i in ('git branch --show-current 2^>nul') do set CHECK_BRANCH=%%i
    if "!CHECK_BRANCH!"=="" set CHECK_BRANCH=%DEFAULT_BRANCH%
    
    REM 检查远程分支是否存在
    git rev-parse --verify origin/!CHECK_BRANCH! >nul 2>&1
    if errorlevel 1 (
        REM 远程分支不存在，检查本地是否有提交
        git rev-parse HEAD >nul 2>&1
        if not errorlevel 1 (
            set HAS_UNPUSHED=1
            echo [提示] 检测到本地有提交但远程分支不存在，需要推送
        )
    ) else (
        REM 远程分支存在，比较本地和远程
        git diff --quiet origin/!CHECK_BRANCH! HEAD 2>nul
        if errorlevel 1 (
            set HAS_UNPUSHED=1
            echo [提示] 检测到本地有未推送的提交
        )
    )
)

if !HAS_UNPUSHED! equ 1 (
    REM 检测当前分支
    set CURRENT_BRANCH=
    for /f "delims=" %%i in ('git branch --show-current 2^>nul') do set CURRENT_BRANCH=%%i
    if "!CURRENT_BRANCH!"=="" set CURRENT_BRANCH=%DEFAULT_BRANCH%
    set /p TARGET_BRANCH=推送到哪个分支？（直接回车默认为 "!CURRENT_BRANCH!"）: 
    if "!TARGET_BRANCH!"=="" set TARGET_BRANCH=!CURRENT_BRANCH!
    
    echo.
    echo 正在推送到 !TARGET_BRANCH! 分支...
    git push -u origin !TARGET_BRANCH!
    if errorlevel 1 (
        echo.
        echo ========================================
        echo   [错误] 推送失败，请检查网络或仓库权限
        echo ========================================
        echo.
    ) else (
        echo.
        echo ========================================
        echo   [完成] 推送成功
        echo ========================================
        echo   本地目录: %cd%
        echo   远程仓库: !FINAL_REPO!
        echo   推送分支: !TARGET_BRANCH!
        if %HAS_STAGED_CHANGES% equ 1 (
            echo   提交信息: !COMMIT_MSG!
        )
        echo   用户: !GIT_NAME! ^<!GIT_EMAIL!^>
        echo ========================================
    )
) else (
    echo.
    echo ========================================
    echo   [提示] 没有需要推送的内容
    echo   - 暂存区无改动
    echo   - 本地无未推送的提交
    echo ========================================
)

echo.
pause
