#!/usr/bin/python
specail='"""'
def printMain(itself): print '#!/usr/bin/python\nspecail=\'%s\'\ndef printMain(itself): %s\nprintMain(r%s%s%s)'%(specail, itself, specail, itself, specail)
printMain(r"""print '#!/usr/bin/python\nspecail=\'%s\'\ndef printMain(itself): %s\nprintMain(r%s%s%s)'%(specail, itself, specail, itself, specail)""")
