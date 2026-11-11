import json, sys
f=sys.argv[1]; want=sys.argv[2] if len(sys.argv)>2 else None
D=json.load(open(f))
for o in D['traces']:
    if want and o['bot']!=want: continue
    print(f"== {o['bot']} t={o['t']} terr={o['terr']} bal={o['bal']} dens={o['bal']/max(1,o['terr']):.1f} cap={o.get('cap')} idle={o.get('idle')} minCmd={o.get('minCmd')} sb={o.get('sb')} dpKeep={o.get('dpKeep')} peopleFloor={o.get('peopleFloor')} winWorth={o.get('winWorth')} neutral={o['neutral']} active={o.get('active')} freeSlot={o.get('freeSlot')} held={o.get('held')} noFull={o.get('isNoFullSend')} boats={o.get('boats')} lastBoat={o.get('lastBoat')} err={o.get('err')}")
    for r in o['nb']:
        print(f"     nb {r['name'][:18]:18} T{r['team']} terr={r['terr']} bal={r['bal']} cnt={r.get('cnt')} person={r.get('person')} price={r.get('price')} allow={r.get('allow')} botOk={r.get('botOk')} floor={r.get('floor')} avail={r.get('avail')} minShare={r.get('minShare')} need={r.get('need')} onMe={r.get('onMe')} mine={r.get('mine')} overMax={r.get('overMax')} send={r.get('send')} {r.get('err','')}")
    if o.get('core'): print('     core',o['core'])
    for r in o.get('offers',[]):
        print('     offer',{k:(v if k!='name' else v[:16]) for k,v in r.items()})
    w=o.get('walk')
    if w:
        print(f"     walk B={w['B']} L={w['L']} fee={w['fee']} worth={w['worth']} cheap={w['cheap']} over={w['over']} minCmd={w['minCmd']} nHumans={w['nHumans']} humanNb={w['humanNbCount']}")
        for r in w['rows']:
            print('       ', {k:(v if k!='name' else v[:16]) for k,v in r.items()})

