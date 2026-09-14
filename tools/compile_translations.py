"""Generate portable gettext catalogs from the shared translation source; no GNU gettext needed.
Django consumes .mo; .po files remain editable translation artifacts.
"""
import json,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
raw=(ROOT/'static/i18n.js').read_text(encoding='utf-8-sig')
data=json.loads(raw.split('window.I18N=',1)[1].strip().rstrip(';'))
extra={
 'Reset your password':['Reset your password','Parolingizni tiklang','Сбросьте пароль'],
 'If you did not request this, ignore this email.':['If you did not request this, ignore this email.','Buni siz so‘ramagan bo‘lsangiz, xatni e’tiborsiz qoldiring.','Если вы не запрашивали это, проигнорируйте письмо.'],
 'This link is invalid or expired.':['This link is invalid or expired.','Havola yaroqsiz yoki muddati tugagan.','Ссылка недействительна или истекла.'],
 'Password changed successfully.':['Password changed successfully.','Parol o‘zgartirildi.','Пароль изменён.'],
 'Log in':['Log in','Kirish','Войти'],
 'Save':['Save','Saqlash','Сохранить'],
 'Email updated successfully.':['Email updated successfully.','Pochta manzili yangilandi.','Электронная почта обновлена.'],
 'New password:':['New password:','Yangi parol:','Новый пароль:'],
 'New password confirmation:':['New password confirmation:','Yangi parolni takrorlang:','Подтверждение нового пароля:'],
}
data.update(extra)
for index,lang in enumerate(['en','uz','ru']):
    messages={v[0]:v[index] for v in data.values()}
    messages['']='Content-Type: text/plain; charset=UTF-8\nLanguage: '+lang+'\nPlural-Forms: nplurals=2; plural=(n != 1);\n'
    folder=ROOT/'locale'/lang/'LC_MESSAGES';folder.mkdir(parents=True,exist_ok=True)
    def quote(s):return json.dumps(s,ensure_ascii=False)
    (folder/'django.po').write_text('\n\n'.join('msgid '+quote(k)+'\nmsgstr '+quote(v) for k,v in sorted(messages.items())),encoding='utf-8')
    keys=sorted(messages);n=len(keys);ids=b'';values=b'';idtable=[];vtable=[];offset=28+16*n
    for k in keys:
        b=k.encode();idtable.append((len(b),offset+len(ids)));ids+=b+b'\0'
    for k in keys:
        b=messages[k].encode();vtable.append((len(b),offset+len(ids)+len(values)));values+=b+b'\0'
    header=struct.pack('<7I',0x950412de,0,n,28,28+8*n,0,0)
    tables=b''.join(struct.pack('<2I',*p) for p in idtable+vtable)
    (folder/'django.mo').write_bytes(header+tables+ids+values)
print('Compiled en, uz and ru Django catalogs.')

