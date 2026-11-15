// Kehai audit: headless mGBA (libmgba 0.10.2) runner. Script on stdin:
//   run N MASK      run N frames holding key mask (1337Boy KEY bits: A=1 B=2 SEL=4 START=8 R=16 L=32 U=64 D=128 R=256 L=512)
//   shot FILE       write framebuffer as PPM
//   peek ADDR LEN   print bytes (mailbox reads)
//   sram FILE       load .sav into SRAM before reset (must come first)
#include <mgba/core/core.h>
#include <mgba/core/log.h>
#include <mgba/gba/core.h>
#include <mgba-util/vfs.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static void nolog(struct mLogger* l,int c,enum mLogLevel lv,const char* f,va_list a){(void)l;(void)c;(void)lv;(void)f;(void)a;}
int main(int argc,char**argv){
  struct mLogger lg={.log=nolog};mLogSetDefaultLogger(&lg);
  struct mCore* c=mCoreFind(argv[1]);if(!c){fprintf(stderr,"no core\n");return 1;}
  c->init(c);mCoreInitConfig(c,NULL);
  unsigned w,h;c->desiredVideoDimensions(c,&w,&h);
  color_t* buf=malloc(w*h*sizeof(color_t));c->setVideoBuffer(c,buf,w);
  if(!mCoreLoadFile(c,argv[1])){fprintf(stderr,"load fail\n");return 1;}
  char line[512];int reset=0;
  if(argc>2){struct VFile* vf=VFileOpen(argv[2],O_RDONLY);if(vf){c->loadSave(c,vf);}}
  c->reset(c);
  while(fgets(line,sizeof line,stdin)){
    char cmd[16],arg[400];unsigned a=0,b=0;
    if(sscanf(line,"%15s",cmd)!=1)continue;
    if(!strcmp(cmd,"run")){sscanf(line,"%*s %u %u",&a,&b);c->setKeys(c,b);for(unsigned i=0;i<a;i++)c->runFrame(c);}
    else if(!strcmp(cmd,"shot")){sscanf(line,"%*s %399s",arg);FILE*f=fopen(arg,"wb");fprintf(f,"P6 %u %u 255\n",w,h);
      for(unsigned i=0;i<w*h;i++){uint32_t p=buf[i];unsigned char px[3]={p&0xFF,(p>>8)&0xFF,(p>>16)&0xFF};fwrite(px,1,3,f);}fclose(f);}
    else if(!strcmp(cmd,"peek")){sscanf(line,"%*s %x %u",&a,&b);for(unsigned i=0;i<b;i++)printf("%02x",c->busRead8(c,a+i));printf("\n");fflush(stdout);}
  }
  return 0;}
