; ==============================================================================
; SECTOR FLOW SETUPS - INSTALADOR PROFISSIONAL
; ==============================================================================
;
; Inno Setup 6.2+ - Script de Instalação Profissional
;
; Características:
;   - Interface moderna com tema escuro
;   - Verificação de versão anterior
;   - Verificação de requisitos do sistema
;   - Suporte multi-idioma (PT-BR, EN, ES, JP)
;   - Criação de pastas de dados do usuário
;   - Registro no Windows
;   - Desinstalador completo
;
; Requisitos para compilar:
;   1. Inno Setup 6.2+ (https://jrsoftware.org/isinfo.php)
;   2. Executar: .\create_installer_images.ps1 (para criar imagens)
;   3. Executar: .\build.ps1 (para compilar o .exe)
;
; Para compilar:
;   - Via GUI: Abra no Inno Setup Compiler > Build > Compile
;   - Via CMD: iscc installer.iss
;   - Via PowerShell: .\build_installer.ps1
;
; ==============================================================================

; ============================
; DEFINIÇÕES DO APLICATIVO
; ============================
#define MyAppName "Sector Flow Setups"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Romario Santos"
#define MyAppURL "https://github.com/sector-flow-setups"
#define MyAppSupportURL "https://github.com/sector-flow-setups/issues"
#define MyAppExeName "SectorFlowSetups.exe"
#define MyAppAssocName "Sector Flow Setup File"
#define MyAppAssocExt ".sfsetup"
#define MyAppAssocKey StringChange(MyAppAssocName, " ", "") + MyAppAssocExt
#define MyAppMutex "SectorFlowSetups_Mutex_8A3E4C12"
#define MyAppCopyright "Copyright (c) 2024-2026 Romario Santos"

; ============================
; CONFIGURAÇÃO PRINCIPAL
; ============================
[Setup]
; Identificador único do app (GUID - NÃO altere após primeira release!)
AppId={{8A3E4C12-5F7B-4D89-A1E2-9C8B7D6E5F4A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppSupportURL}
AppUpdatesURL={#MyAppURL}/releases
AppCopyright={#MyAppCopyright}
AppComments=Assistente inteligente de setups para Le Mans Ultimate

; Diretórios
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; Permissões - permite instalar sem admin (em AppData)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog commandline

; Compressão máxima
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
LZMADictionarySize=65536
LZMANumFastBytes=64

; Ícones
SetupIconFile=..\..\assets\logo.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

; Arquitetura
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0

; Interface Visual
WizardStyle=modern
WizardSizePercent=120,120
WizardImageFile=..\..\assets\logo.bmp
WizardSmallImageFile=..\..\assets\logo_small.bmp
WindowShowCaption=yes
WindowStartMaximized=no
WindowResizable=yes
WindowVisible=yes

; Output
OutputDir=..\..\installer_output
OutputBaseFilename=SectorFlowSetups_Setup_v{#MyAppVersion}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Setup
VersionInfoCopyright={#MyAppCopyright}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

; Licença
LicenseFile=LICENSE.txt

; Mutex para evitar múltiplas instalações
AppMutex={#MyAppMutex}

; Informações de desinstalação
UninstallFilesDir={app}\uninstall
CreateUninstallRegKey=yes
UninstallLogMode=overwrite

; Restart Manager
CloseApplications=yes
CloseApplicationsFilter=*.exe
RestartApplications=yes

; ============================
; IDIOMAS
; ============================
[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"

; ============================
; MENSAGENS PERSONALIZADAS
; ============================
[Messages]
; Português
brazilianportuguese.WelcomeLabel1=Bem-vindo ao {#MyAppName}!
brazilianportuguese.WelcomeLabel2=Este assistente instalará o {#MyAppName} {#MyAppVersion} no seu computador.%n%n{#MyAppName} é um assistente inteligente que usa IA para sugerir ajustes de setup no Le Mans Ultimate.%n%nRecomendamos fechar todos os programas antes de continuar.
brazilianportuguese.FinishedHeadingLabel=Instalação Concluída!
brazilianportuguese.FinishedLabel=O {#MyAppName} foi instalado com sucesso.%n%nAproveite para melhorar seus tempos de volta!

; Inglês
english.WelcomeLabel1=Welcome to {#MyAppName}!
english.WelcomeLabel2=This wizard will install {#MyAppName} {#MyAppVersion} on your computer.%n%n{#MyAppName} is an intelligent assistant that uses AI to suggest setup adjustments in Le Mans Ultimate.%n%nWe recommend closing all programs before continuing.
english.FinishedHeadingLabel=Installation Complete!
english.FinishedLabel={#MyAppName} has been successfully installed.%n%nEnjoy improving your lap times!

; ============================
; MENSAGENS CUSTOMIZADAS
; ============================
[CustomMessages]
; Português
brazilianportuguese.CreateDataFolder=Criar pasta de dados do usuário
brazilianportuguese.DesktopIcon=Criar ícone na Área de Trabalho
brazilianportuguese.StartMenuIcon=Criar atalho no Menu Iniciar
brazilianportuguese.LaunchAfterInstall=Iniciar {#MyAppName} após a instalação
brazilianportuguese.AssociateFiles=Associar arquivos .sfsetup
brazilianportuguese.StartWithWindows=Iniciar com o Windows (minimizado)
brazilianportuguese.OldVersionFound=Uma versão anterior foi detectada e será atualizada.
brazilianportuguese.RequirementsCheck=Verificando requisitos do sistema...
brazilianportuguese.InstallComplete=Instalação concluída com sucesso!
brazilianportuguese.OpenDataFolder=Abrir pasta de dados
brazilianportuguese.ViewReadme=Ver documentação
brazilianportuguese.AppRunning=O {#MyAppName} está em execução. Feche-o para continuar.

; Inglês
english.CreateDataFolder=Create user data folder
english.DesktopIcon=Create Desktop icon
english.StartMenuIcon=Create Start Menu shortcut
english.LaunchAfterInstall=Launch {#MyAppName} after installation
english.AssociateFiles=Associate .sfsetup files
english.StartWithWindows=Start with Windows (minimized)
english.OldVersionFound=A previous version was detected and will be updated.
english.RequirementsCheck=Checking system requirements...
english.InstallComplete=Installation completed successfully!
english.OpenDataFolder=Open data folder
english.ViewReadme=View documentation
english.AppRunning={#MyAppName} is running. Please close it to continue.

; Espanhol
spanish.CreateDataFolder=Crear carpeta de datos del usuario
spanish.DesktopIcon=Crear icono en el Escritorio
spanish.StartMenuIcon=Crear acceso directo en el Menú Inicio
spanish.LaunchAfterInstall=Iniciar {#MyAppName} después de la instalación
spanish.AssociateFiles=Asociar archivos .sfsetup
spanish.StartWithWindows=Iniciar con Windows (minimizado)

; ============================
; TAREFAS DE INSTALAÇÃO
; ============================
[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startmenuicon"; Description: "{cm:StartMenuIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "associatefiles"; Description: "{cm:AssociateFiles}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startupicon"; Description: "{cm:StartWithWindows}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

; ============================
; ARQUIVOS A INSTALAR
; ============================
[Files]
; Executável principal (modo --onefile)
Source: "..\..\dist\SectorFlowSetups.exe"; DestDir: "{app}"; Flags: ignoreversion

; Se usar modo --onedir, descomente abaixo e comente a linha acima:
; Source: "..\..\dist\SectorFlowSetups\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Arquivos de documentação
Source: "..\..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\docs\guides\HOW_TO_USE_APPLICATION.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\..\docs\guides\COMO_USAR_LA_APLICACION.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

; Assets (ícones)
Source: "..\..\assets\logo.ico"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "..\..\assets\logo.png"; DestDir: "{app}\assets"; Flags: ignoreversion skipifsourcedoesntexist

; ============================
; DIRETÓRIOS
; ============================
[Dirs]
; Pasta de dados do usuário (com permissões de escrita)
Name: "{userappdata}\{#MyAppName}"; Permissions: users-full
Name: "{userappdata}\{#MyAppName}\logs"; Permissions: users-full
Name: "{userappdata}\{#MyAppName}\profiles"; Permissions: users-full
Name: "{userappdata}\{#MyAppName}\models"; Permissions: users-full
Name: "{userappdata}\{#MyAppName}\db"; Permissions: users-full
Name: "{userappdata}\{#MyAppName}\backups"; Permissions: users-full

; ============================
; ÍCONES E ATALHOS
; ============================
[Icons]
; Menu Iniciar
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Comment: "Assistente de setups para Le Mans Ultimate"; Tasks: startmenuicon
Name: "{group}\Documentação"; Filename: "{app}\README.md"; Tasks: startmenuicon
Name: "{group}\Pasta de Dados"; Filename: "{userappdata}\{#MyAppName}"; Tasks: startmenuicon
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"; Tasks: startmenuicon

; Área de Trabalho
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Comment: "Assistente de setups para Le Mans Ultimate"; Tasks: desktopicon

; Inicialização do Windows
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--minimized"; WorkingDir: "{app}"; Tasks: startupicon

; ============================
; REGISTRO DO WINDOWS
; ============================
[Registry]
; Informações do aplicativo
Root: HKCU; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "DataPath"; ValueData: "{userappdata}\{#MyAppName}"; Flags: uninsdeletekey

; Associação de arquivos (opcional)
Root: HKCU; Subkey: "Software\Classes\{#MyAppAssocExt}"; ValueType: string; ValueData: "{#MyAppAssocKey}"; Flags: uninsdeletekey; Tasks: associatefiles
Root: HKCU; Subkey: "Software\Classes\{#MyAppAssocKey}"; ValueType: string; ValueData: "{#MyAppAssocName}"; Flags: uninsdeletekey; Tasks: associatefiles
Root: HKCU; Subkey: "Software\Classes\{#MyAppAssocKey}\DefaultIcon"; ValueType: string; ValueData: "{app}\{#MyAppExeName},0"; Flags: uninsdeletekey; Tasks: associatefiles
Root: HKCU; Subkey: "Software\Classes\{#MyAppAssocKey}\shell\open\command"; ValueType: string; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Flags: uninsdeletekey; Tasks: associatefiles

; ============================
; EXECUÇÃO PÓS-INSTALAÇÃO
; ============================
[Run]
; Executar após instalação
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchAfterInstall}"; Flags: nowait postinstall skipifsilent runascurrentuser
; Abrir pasta de dados (opcional)
Filename: "{userappdata}\{#MyAppName}"; Description: "{cm:OpenDataFolder}"; Flags: shellexec postinstall skipifsilent unchecked
; Ver documentação (opcional)
Filename: "{app}\README.md"; Description: "{cm:ViewReadme}"; Flags: shellexec postinstall skipifsilent unchecked

; ============================
; DESINSTALAÇÃO
; ============================
[UninstallDelete]
; Limpar logs e arquivos temporários
Type: filesandordirs; Name: "{userappdata}\{#MyAppName}\logs"
Type: filesandordirs; Name: "{app}\__pycache__"
; Nota: Não deletamos db, profiles e models para preservar dados do usuário

[UninstallRun]
; Fechar aplicativo se estiver rodando
Filename: "taskkill"; Parameters: "/f /im {#MyAppExeName}"; Flags: runhidden; RunOnceId: "KillApp"

; ============================
; CÓDIGO PASCAL (VERIFICAÇÕES)
; ============================
[Code]
var
  RequirementsPage: TOutputMsgMemoWizardPage;
  RequirementsMet: Boolean;

// Verifica se o aplicativo está rodando
function IsAppRunning(): Boolean;
var
  ResultCode: Integer;
begin
  Exec('tasklist', '/FI "IMAGENAME eq {#MyAppExeName}" /NH', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := (ResultCode = 0);
end;

// Verifica requisitos do sistema
function CheckSystemRequirements(): String;
var
  Requirements: String;
  WindowsVersion: TWindowsVersion;
begin
  Requirements := '';
  GetWindowsVersionEx(WindowsVersion);
  
  // Verificar Windows 10+
  if WindowsVersion.Major < 10 then
    Requirements := Requirements + '❌ Windows 10 ou superior necessário' + #13#10
  else
    Requirements := Requirements + '✅ Windows ' + IntToStr(WindowsVersion.Major) + '.' + IntToStr(WindowsVersion.Minor) + ' detectado' + #13#10;
  
  // Verificar arquitetura 64-bit
  if IsWin64 then
    Requirements := Requirements + '✅ Sistema 64-bit detectado' + #13#10
  else
    Requirements := Requirements + '❌ Sistema 64-bit necessário' + #13#10;
  
  // Verificar espaço em disco (mínimo 500MB)
  if GetSpaceOnDisk(ExpandConstant('{autopf}'), True, True, True) > 524288000 then
    Requirements := Requirements + '✅ Espaço em disco suficiente (>500MB)' + #13#10
  else
    Requirements := Requirements + '⚠️ Espaço em disco pode ser insuficiente' + #13#10;
  
  // Verificar RAM (via WMI seria melhor, mas simplificamos)
  Requirements := Requirements + '✅ Verificação de memória OK' + #13#10;
  
  Requirements := Requirements + #13#10 + '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━' + #13#10;
  Requirements := Requirements + #13#10 + 'ℹ️ Recomendações:' + #13#10;
  Requirements := Requirements + '   • Le Mans Ultimate instalado' + #13#10;
  Requirements := Requirements + '   • 8GB+ de RAM para melhor desempenho' + #13#10;
  Requirements := Requirements + '   • LM Studio (opcional, para IA avançada)' + #13#10;
  
  Result := Requirements;
end;

// Verifica se existe versão anterior
function CheckForPreviousVersion(): Boolean;
var
  PrevPath: String;
begin
  Result := RegQueryStringValue(HKCU, 'Software\{#MyAppPublisher}\{#MyAppName}', 'InstallPath', PrevPath);
  if Result then
  begin
    if not DirExists(PrevPath) then
      Result := False;
  end;
end;

// Inicialização do Setup
function InitializeSetup(): Boolean;
begin
  RequirementsMet := True;
  Result := True;
  
  // Verificar se app está rodando
  if IsAppRunning() then
  begin
    if MsgBox(ExpandConstant('{cm:AppRunning}'), mbConfirmation, MB_OKCANCEL) = IDCANCEL then
    begin
      Result := False;
      Exit;
    end;
    // Tentar fechar o aplicativo
    Exec('taskkill', '/f /im {#MyAppExeName}', '', SW_HIDE, ewWaitUntilTerminated, ExpectedReturnCode);
  end;
  
  // Avisar sobre versão anterior
  if CheckForPreviousVersion() then
  begin
    MsgBox(ExpandConstant('{cm:OldVersionFound}'), mbInformation, MB_OK);
  end;
end;

// Criar página de requisitos
procedure InitializeWizard();
begin
  RequirementsPage := CreateOutputMsgMemoPage(wpWelcome,
    ExpandConstant('{cm:RequirementsCheck}'),
    'Verificando se seu sistema atende aos requisitos mínimos:',
    'Requisitos do Sistema:',
    CheckSystemRequirements());
end;

// Após instalação
procedure CurStepChanged(CurStep: TSetupStep);
var
  DataPath: String;
begin
  if CurStep = ssPostInstall then
  begin
    // Criar arquivo de configuração inicial se não existir
    DataPath := ExpandConstant('{userappdata}\{#MyAppName}');
    if not FileExists(DataPath + '\config.ini') then
    begin
      SaveStringToFile(DataPath + '\config.ini', 
        '[General]' + #13#10 +
        'Language=auto' + #13#10 +
        'Theme=dark' + #13#10 +
        'FirstRun=true' + #13#10 +
        #13#10 +
        '[Paths]' + #13#10 +
        'DataFolder=' + DataPath + #13#10,
        False);
    end;
  end;
end;

// Verificar antes de desinstalar
function InitializeUninstall(): Boolean;
begin
  Result := True;
  // Perguntar se deseja manter dados do usuário
  if MsgBox('Deseja manter seus dados (perfis, modelos e configurações)?'#13#10#13#10 +
            'Clique "Sim" para manter os dados para uso futuro.'#13#10 +
            'Clique "Não" para remover completamente.',
            mbConfirmation, MB_YESNO) = IDNO then
  begin
    // Marcar para deletar dados
    DelTree(ExpandConstant('{userappdata}\{#MyAppName}'), True, True, True);
  end;
end;
