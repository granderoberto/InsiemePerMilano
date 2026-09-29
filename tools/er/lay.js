const ELK=require('elkjs');const fs=require('fs');
new ELK().layout(JSON.parse(fs.readFileSync('in.json'))).then(r=>{fs.writeFileSync('out.json',JSON.stringify(r));console.log('W',r.width,'H',r.height)}).catch(e=>{console.error(e);process.exit(1)});
