// @vega-provider movieBox
// @vega-version 2.5
"use strict";var __defProp=Object.defineProperty,__getOwnPropDesc=Object.getOwnPropertyDescriptor,__getOwnPropNames=Object.getOwnPropertyNames,__hasOwnProp=Object.prototype.hasOwnProperty,__name=(target,value)=>__defProp(target,"name",{value:value,configurable:!0}),__export=(target,all)=>{for(var name in all)__defProp(target,name,{get:all[name],enumerable:!0})},__copyProps=(to,from,except,desc)=>{if(from&&"object"==typeof from||"function"==typeof from)for(let key of __getOwnPropNames(from))__hasOwnProp.call(to,key)||key===except||__defProp(to,key,{get:()=>from[key],enumerable:!(desc=__getOwnPropDesc(from,key))||desc.enumerable});return to},__toCommonJS=mod=>__copyProps(__defProp({},"__esModule",{value:!0}),mod),__async=(__this,__arguments,generator)=>new Promise((resolve,reject)=>{var fulfilled=value=>{try{step(generator.next(value))}catch(e){reject(e)}},rejected=value=>{try{step(generator.throw(value))}catch(e){reject(e)}},step=x=>x.done?resolve(x.value):Promise.resolve(x.value).then(fulfilled,rejected);step((generator=generator.apply(__this,__arguments)).next())}),stream_exports={};__export(stream_exports,{getStream:()=>getStream});var getStream=__name(function(_0){return __async(this,arguments,function*({link:url,type:type,providerContext:providerContext}){const{axios:axios,cheerio:cheerio}=providerContext;try{const stream=[],data=JSON.parse(url);if(!data.url){return [];}
// SMART CHECK: Verify if the video link is actually alive before giving it to the player
try{
    // Send a GET request asking for only the first byte (0-0)
    const check = yield fetch(data.url, { 
        method: 'GET', 
        headers: { 'Range': 'bytes=0-0', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)' } 
    });
    
    // 200 (OK) or 206 (Partial Content) means the link is alive
    if(!check.ok && check.status !== 206 && check.status !== 403){
        console.log("Dead link detected, skipping:", data.url);
        return []; // Return empty so player knows it failed quickly
    }
}catch(e){
    console.log("Link check failed, skipping:", data.url);
    return []; 
}

// If alive, push to stream
stream.push({link:data.url,server:data.title||"Unknown Server",type:"mp4"});
console.log("stream",stream);
return stream;
}catch(err){return console.log("getStream error",err),[]}})},"getStream");exports.getStream=getStream;
