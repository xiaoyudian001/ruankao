'use client';
import {useCallback,useMemo,useState} from 'react';
import {DraftWorkspace,emptyDraft,type Draft,type EditorDraft} from '../../lib/textbook/drafts';
export function useDraftWorkspace(ownerId:string){
 const work=useMemo(()=>new DraftWorkspace({getItem:k=>window.localStorage.getItem(k),setItem:(k,v)=>window.localStorage.setItem(k,v),removeItem:k=>window.localStorage.removeItem(k)},ownerId),[ownerId]);
 const [value,setValue]=useState<EditorDraft>(emptyDraft),[status,setStatus]=useState('');
 const publish=useCallback(()=>{setValue({...work.value});setStatus(work.status);},[work]);
 const update=useCallback((change:Partial<EditorDraft>)=>{work.update(change);publish();},[work,publish]);
 const setDraft=useCallback((text:string|((previous:string)=>string))=>update({text:typeof text==='function'?text(work.value.text):text}),[update,work]);
 const setMode=useCallback((mode:Draft['mode'])=>update({mode}),[update]);
 const setTaskType=useCallback((taskType:Draft['taskType'])=>update({taskType,screenshot:null}),[update]);
 const setScreenshot=useCallback((screenshot:EditorDraft['screenshot'])=>update({screenshot}),[update]);
 const openDraft=useCallback((session:string|null,override?:EditorDraft,preserveSaved=false)=>{work.open(session,override,preserveSaved);publish();},[work,publish]);
 const clearDraft=useCallback(()=>{work.clear();publish();},[work,publish]);
 const completeDraft=useCallback((source:string|null,target:string|null,submitted:Draft)=>{work.complete(source,target,submitted);publish();},[work,publish]);
 return {draft:value.text,mode:value.mode,taskType:value.taskType,screenshot:value.screenshot,retrySource:value.retrySource,draftStatus:status,setDraft,setMode,setTaskType,setScreenshot,openDraft,clearDraft,completeDraft,setEditor:update};
}
