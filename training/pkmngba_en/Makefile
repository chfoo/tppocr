.PHONY: all pkmngb

all: pkmngb

pkmngb:
	text2image --text=training_text.txt \
		--outputbase=pkmngba_en.PokemonDPPt.exp0 \
		--font='Pokemon DPPt' --fonts_dir=../pkmn_dppt_font/
	tesseract pkmngba_en.PokemonDPPt.exp0.tif pkmngba_en.PokemonDPPt.exp0 box.train.stderr
	unicharset_extractor pkmngba_en.PokemonDPPt.exp0.box
	mftraining -F font_properties -U unicharset -O pkmngba_en.unicharset pkmngba_en.PokemonDPPt.exp0.tr
	cntraining pkmngba_en.PokemonDPPt.exp0.tr
	wordlist2dawg ../word_lists/word_list.txt pkmngba_en.word-dawg pkmngba_en.unicharset
	wordlist2dawg ../word_lists/top_100_word_list.txt pkmngba_en.freq-dawg pkmngba_en.unicharset

	mv shapetable pkmngba_en.shapetable
	mv normproto pkmngba_en.normproto
	mv inttemp pkmngba_en.inttemp
	mv pffmtable pkmngba_en.pffmtable
	mv unicharset pkmngba_en.unicharset

	combine_tessdata pkmngba_en.

