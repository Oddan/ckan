(custom-set-variables
 ;; custom-set-variables was added by Custom.
 ;; If you edit it by hand, you could mess it up, so be careful.
 ;; Your init file should contain only one such instance.
 ;; If there is more than one, they won't work right.
 '(python-shell-interpreter "ipython")
 '(python-shell-interpreter-args "-i --simple-prompt"))
(custom-set-faces
 ;; custom-set-faces was added by Custom.
 ;; If you edit it by hand, you could mess it up, so be careful.
 ;; Your init file should contain only one such instance.
 ;; If there is more than one, they won't work right.
 )
(elpy-enable)
(require 'package)
(add-to-list
 'package-archives
 '("melpa-stable" . "http://stable.melpa.org/packages/")
 t)
(add-to-list
 'package-archives
 '("melpa" . "http://melpa.org/packages/")
 t)

(package-initialize)
(require 'mic-paren)
(paren-activate)
(setf paren-priority 'close)


(require 'iedit)
(global-set-key (kbd "C-o")
		(lambda (arg)
		  (interactive "P")
		  (if (bound-and-true-p iedit-mode)
		      (iedit-mode -1)
		    (iedit-mode))))

(global-set-key (kbd "C-M-o") 'ace-jump-mode)


