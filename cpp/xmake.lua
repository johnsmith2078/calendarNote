add_rules("mode.debug", "mode.release")

set_arch("x64")
set_languages("c++17")

local qt_dir = os.getenv("QT_DIR") or "D:\\Qt\\Qt5.9.9\\5.9.9\\msvc2017_64"
if not os.isdir(qt_dir) then
    qt_dir = "D:\\Qt\\6.8.1\\mingw_64"
end

local qt_bin_dir = path.join(qt_dir, "bin")
local qt_inc_dir = path.join(qt_dir, "include")
local qt_lib_dir = path.join(qt_dir, "lib")
local qt_major = "5"
if os.isfile(path.join(qt_lib_dir, "Qt6Core.lib")) or os.isfile(path.join(qt_lib_dir, "libQt6Core.a")) then
    qt_major = "6"
end

set_config("qt", qt_dir)

target("calendarNote")
    set_kind("binary")

    add_files("src/*.cpp")
    add_files("src/resources.qrc")
    add_files("src/app.rc")

    add_includedirs(qt_inc_dir)
    add_includedirs(path.join(qt_inc_dir, "QtCore"))
    add_includedirs(path.join(qt_inc_dir, "QtGui"))
    add_includedirs(path.join(qt_inc_dir, "QtWidgets"))
    add_includedirs(path.join(qt_inc_dir, "QtNetwork"))
    add_linkdirs(qt_lib_dir)

    local qt_suffix = ""
    if is_mode("debug") and os.isfile(path.join(qt_lib_dir, "Qt" .. qt_major .. "Cored.lib")) then
        qt_suffix = "d"
    end
    add_links("Qt" .. qt_major .. "Widgets" .. qt_suffix)
    add_links("Qt" .. qt_major .. "Gui" .. qt_suffix)
    add_links("Qt" .. qt_major .. "Network" .. qt_suffix)
    add_links("Qt" .. qt_major .. "Core" .. qt_suffix)
    add_links("user32", "shell32")
    if qt_major == "5" and not is_plat("mingw") then
        add_links("qtmain" .. qt_suffix)
    end

    add_defines("UNICODE", "_UNICODE")
    if is_mode("release") then
        add_defines("QT_NO_DEBUG")
    end

    if is_plat("mingw") then
        add_cxflags("-finput-charset=UTF-8")
        add_ldflags("-mwindows", "-Wl,--subsystem,windows")
    else
        add_cxflags("/utf-8")
        add_ldflags("/subsystem:windows")
    end

    add_rules("qt.qrc", { rcc = path.join(qt_bin_dir, "rcc.exe") })

    after_build(function (target)
        if is_mode("debug") then
            print("[pack] skipped in debug mode")
            return
        end

        local windeployqt = path.join(qt_bin_dir, qt_major == "6" and "windeployqt6.exe" or "windeployqt.exe")
        if not os.isfile(windeployqt) then
            windeployqt = path.join(qt_bin_dir, "windeployqt.exe")
        end

        local enigmavb = "D:\\Program Files (x86)\\Enigma Virtual Box\\enigmavbconsole.exe"
        local bindir = target:targetdir()
        local exe_name = target:name() .. ".exe"
        local src_exe = path.join(bindir, exe_name)
        local deploy_dir = path.join(bindir, "_deploy")
        local deploy_exe = path.join(deploy_dir, exe_name)

        os.tryrm(deploy_dir)
        os.mkdir(deploy_dir)
        os.cp(src_exe, deploy_dir)

        if os.isfile(windeployqt) then
            print("[pack] windeployqt ...")
            os.runv(windeployqt, { deploy_exe, "--no-translations", "--no-opengl-sw" })
        else
            print("[pack] WARNING: windeployqt not found under " .. qt_bin_dir)
        end

        local function indent(n)
            return string.rep("\t", n)
        end

        local function scan(scan_dir)
            local entries = {}
            for _, d in ipairs(os.dirs(path.join(scan_dir, "*"))) do
                table.insert(entries, { etype = 3, name = path.filename(d), children = scan(d) })
            end
            for _, f in ipairs(os.files(path.join(scan_dir, "*"))) do
                local name = path.filename(f)
                if name ~= exe_name then
                    table.insert(entries, { etype = 2, name = name })
                end
            end
            return entries
        end

        local function write_file(e, depth, disk_dir)
            local s = indent(depth) .. "<File>\n"
            depth = depth + 1
            s = s .. indent(depth) .. "<Type>" .. e.etype .. "</Type>\n"
            s = s .. indent(depth) .. "<Name>" .. e.name .. "</Name>\n"
            if e.etype == 2 then
                s = s .. indent(depth) .. "<File>" .. path.absolute(path.join(disk_dir, e.name)) .. "</File>\n"
                s = s .. indent(depth) .. "<ActiveX>False</ActiveX>\n"
                s = s .. indent(depth) .. "<ActiveXInstall>False</ActiveXInstall>\n"
                s = s .. indent(depth) .. "<Action>0</Action>\n"
                s = s .. indent(depth) .. "<OverwriteDateTime>False</OverwriteDateTime>\n"
                s = s .. indent(depth) .. "<OverwriteAttributes>False</OverwriteAttributes>\n"
                s = s .. indent(depth) .. "<PassCommandLine>False</PassCommandLine>\n"
                s = s .. indent(depth) .. "<HideFromDialogs>0</HideFromDialogs>\n"
            else
                s = s .. indent(depth) .. "<Action>0</Action>\n"
                s = s .. indent(depth) .. "<OverwriteDateTime>False</OverwriteDateTime>\n"
                s = s .. indent(depth) .. "<OverwriteAttributes>False</OverwriteAttributes>\n"
                s = s .. indent(depth) .. "<HideFromDialogs>0</HideFromDialogs>\n"
                s = s .. indent(depth) .. "<Files>\n"
                local child_dir = path.join(disk_dir, e.name)
                for _, child in ipairs(e.children) do
                    s = s .. write_file(child, depth + 1, child_dir)
                end
                s = s .. indent(depth) .. "</Files>\n"
            end
            return s .. indent(depth - 1) .. "</File>\n"
        end

        local files_xml = ""
        for _, e in ipairs(scan(deploy_dir)) do
            files_xml = files_xml .. write_file(e, 4, deploy_dir)
        end

        local boxed_exe = path.join(bindir, target:name() .. "_single.exe")
        local evb_file = path.join(bindir, target:name() .. ".evb")
        local evb_text = table.concat({
            '<?xml version="1.0" encoding="windows-1252"?>',
            "<>",
            "\t<InputFile>" .. path.absolute(deploy_exe) .. "</InputFile>",
            "\t<OutputFile>" .. path.absolute(boxed_exe) .. "</OutputFile>",
            "\t<Files>",
            "\t\t<Enabled>True</Enabled>",
            "\t\t<DeleteExtractedOnExit>False</DeleteExtractedOnExit>",
            "\t\t<CompressFiles>True</CompressFiles>",
            "\t\t<Files>",
            "\t\t\t<File>",
            "\t\t\t\t<Type>3</Type>",
            "\t\t\t\t<Name>%DEFAULT FOLDER%</Name>",
            "\t\t\t\t<Action>0</Action>",
            "\t\t\t\t<OverwriteDateTime>False</OverwriteDateTime>",
            "\t\t\t\t<OverwriteAttributes>False</OverwriteAttributes>",
            "\t\t\t\t<HideFromDialogs>0</HideFromDialogs>",
            "\t\t\t\t<Files>",
            files_xml,
            "\t\t\t\t</Files>",
            "\t\t\t</File>",
            "\t\t</Files>",
            "\t</Files>",
            "\t<Registries><Enabled>False</Enabled><Registries></Registries></Registries>",
            "\t<Packaging><Enabled>False</Enabled></Packaging>",
            "\t<Options>",
            "\t\t<ShareVirtualSystem>True</ShareVirtualSystem>",
            "\t\t<MapExecutableWithTemporaryFile>True</MapExecutableWithTemporaryFile>",
            "\t\t<AllowRunningOfVirtualExeFiles>True</AllowRunningOfVirtualExeFiles>",
            "\t</Options>",
            "\t<Storage><Files><Enabled>False</Enabled></Files></Storage>",
            "</>",
            ""
        }, "\n")

        io.writefile(evb_file, evb_text)
        if os.isfile(enigmavb) then
            print("[pack] enigmavbconsole ...")
            os.runv(enigmavb, { path.absolute(evb_file) })
            if os.isfile(boxed_exe) then
                print("[pack] single exe: " .. boxed_exe)
            end
        else
            print("[pack] WARNING: Enigma Virtual Box not found, deploy dir: " .. deploy_dir)
        end
    end)
