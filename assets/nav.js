const menuButton=document.querySelector('.menu-toggle');
const mainNav=document.querySelector('#main-nav');
if(menuButton&&mainNav){menuButton.addEventListener('click',()=>{const open=mainNav.classList.toggle('open');menuButton.setAttribute('aria-expanded',String(open))});mainNav.addEventListener('click',()=>{mainNav.classList.remove('open');menuButton.setAttribute('aria-expanded','false')})}
