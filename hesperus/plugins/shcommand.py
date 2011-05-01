from hesperus.plugin import CommandPlugin
import urllib, urllib2, json
from ..core import ConfigurationError, ET

import subprocess

def _short_url(url):
    if not url:
        return None
    
    apiurl = 'https://www.googleapis.com/urlshortener/v1/url'
    data = json.dumps({'longUrl' : url})
    headers = {'Content-Type' : 'application/json'}
    r = urllib2.Request(apiurl, data, headers)
    
    try:
        retdata = urllib2.urlopen(r).read()
        retdata = json.loads(retdata)
        return retdata.get('id', url)
    except urllib2.URLError:
        return url
    except ValueError:
        return url

filters = {'shorturl' : _short_url}

def check_output(*args, **kwargs):
    kwargs['stdout'] = subprocess.PIPE
    # will hang for HUGE output... you were warned
    p = subprocess.Popen(*args, **kwargs)
    returncode = p.wait()
    if returncode:
        raise subprocess.CalledProcessError(returncode, args)
    return p.communicate()[0]

class ShCommandPlugin(CommandPlugin):
    @CommandPlugin.config_types(commands = ET.Element)
    def __init__(self, core, commands=None):
        super(CommandPlugin, self).__init__(core)
        
        self.commands = {}
        
        if commands == None:
            commands = []
        for el in commands:
            if not el.tag.lower() == 'command':
                raise ConfigurationError('commands must contain command tags')
            name = el.get('name', None)
            if name == None:
                raise ConfigurationError('command tags must have a name')
            filt = el.get('filter', None)
            if filt and not filt in filters:
                raise ConfigurationError('invalid command filter')
            if filt:
                filt = filters[filt]
            else:
                filt = lambda s: s
            command = el.text.strip()
            
            self.commands[name.lower()] = (command, filt)
        
    @CommandPlugin.register_command(r"(\S+)(?:\s+(.+))?")
    def list_command(self, chans, match, direct, reply):
        cmd = match.group(1).lower()
        if not cmd in self.commands:
            return

        cmd, filt = self.commands[cmd]
        args = match.group(2)
        if not args:
            args = ""
        args = " " + args
        
        try:
            output = check_output(cmd + args, shell=True)
            output = filt(output)
            reply(output)
        except subprocess.CalledProcessError:
            self.log_error("could not run command \"%s\"" % (match.group(1),))
            reply("command failed, please tell bot operator")