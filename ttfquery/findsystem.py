"""Find system fonts (only works on Linux and Win32 at the moment)"""
import sys, os, glob, re

def win32FontDirectory( ):
    """Get User-specific font directory on Win32"""
    try:
        import _winreg
    except ImportError:
        return os.path.join(os.environ['WINDIR'], 'Fonts')
    else:
        k = _winreg.OpenKey(
            _winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
        )
        try:
            # should check that k is valid? How?
            return _winreg.QueryValueEx( k, "Fonts" )[0]
        finally:
            _winreg.CloseKey( k )

def win32InstalledFonts( fontDirectory = None ):
    """Get list of explicitly *installed* font names"""
    import _winreg
    if fontDirectory is None:
        fontDirectory = win32FontDirectory()
    k = None
    items = {}
    for keyName in (
        r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts",
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Fonts",
    ):
        try:
            k = _winreg.OpenKey(
                _winreg.HKEY_LOCAL_MACHINE,
                keyName
            )
        except OSError, err:
            pass
    if not k:
        # couldn't open either WinNT or Win98 key???
        return glob.glob( os.path.join(fontDirectory, '*.ttf'))
    try:
        # should check that k is valid? How?
        for index in range( _winreg.QueryInfoKey(k)[1]):
            key,value,_ = _winreg.EnumValue( k, index )
            if not os.path.dirname( value ):
                value = os.path.join( fontDirectory, value )
            value = os.path.abspath( value ).lower()
            if value[-4:] == '.ttf':
                items[ value ] = 1
        return items.keys()
    finally:
        _winreg.CloseKey( k )
    

def linuxFontDirectories( ):
    """Get system font directories on Linux/Unix
    
    Uses /usr/sbin/chkfontpath to get the list
    of system-font directories, note that many
    of these will *not* be truetype font directories.

    If /usr/sbin/chkfontpath isn't available, uses
    returns a set of common Linux/Unix paths
    """
    executable = '/usr/sbin/chkfontpath'
    if os.path.isfile( executable ):
        data = os.popen( executable ).readlines()
        match = re.compile( '\d+: (.+)')
        set = []
        for line in data:
            result = match.match( line )
            if result:
                set.append(result.group(1))
        return set
    else:
        directories = [
            # what seems to be the standard installation point
            "/usr/X11R6/lib/X11/fonts/TTF/",
            # common application, not really useful
            "/usr/lib/openoffice/share/fonts/truetype/",
            # documented as a good place to install new fonts...
            "/usr/share/fonts",
            "/usr/local/share/fonts",
            # seems to be where fonts are installed for an individual user?
            "~/.fonts",
            # okay, now the OS X variants...
            "~/Library/Fonts/",
            "/Library/Fonts/",
            "/Network/Library/Fonts/",
            "/System/Library/Fonts/",
            "System Folder:Fonts:",
        ]
        
        set = []
        def add( arg, directory, files):
            set.append( directory )
        for directory in directories:
            directory = directory = os.path.expanduser( os.path.expandvars(directory))
            try:
                if os.path.isdir( directory ):
                    os.path.walk(directory, add, ())
            except (IOError, OSError, TypeError, ValueError):
                pass
        return set

def findFonts(paths = None):
    """Find fonts in paths, or the system paths if not given

    XXX Doesn't current support OS-X system paths
    """
    files = {}
    if paths is None:
        if sys.platform == 'win32':
            fontDirectory = win32FontDirectory()
            paths = [
                fontDirectory,
            ]
            # now get all installed fonts directly...
            for f in win32InstalledFonts(fontDirectory):
                # yes, it's inefficient, the interface
                # for win32InstalledFonts really should be
                # using sets, not lists
                files[f] = 1
        else:
            paths = linuxFontDirectories()
    elif isinstance( paths, (str, unicode)):
        paths = [paths]
    for path in paths:
        for file in glob.glob( os.path.join(path, '*.ttf')):
            files[os.path.abspath(file)] = 1
    return files.keys()

if __name__ == "__main__":
    print 'linux font directories', linuxFontDirectories()
    print 'font names', findFonts()
